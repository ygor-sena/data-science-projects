import threading
from types import SimpleNamespace

import pytest
from django.db import connection, connections
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from estoque.models import MovimentacaoEstoque, Produto
from estoque.serializers import MovimentacaoSerializer

pytestmark = pytest.mark.django_db

URL = "/api/movimentacoes/"


def movimentar(api, produto, tipo, quantidade, observacao=""):
    return api.post(
        URL,
        {
            "produto": produto.id,
            "tipo": tipo,
            "quantidade": quantidade,
            "observacao": observacao,
        },
        format="json",
    )


class TestEntrada:
    def test_entrada_aumenta_o_estoque(self, api, criar_produto):
        produto = criar_produto(quantidade_estoque=10)

        resposta = movimentar(api, produto, "ENTRADA", 5)

        assert resposta.status_code == 201
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 15

    def test_entrada_registra_a_movimentacao(self, api, usuario, produto):
        resposta = movimentar(api, produto, "ENTRADA", 5, "Nota 123")

        mov = MovimentacaoEstoque.objects.get(id=resposta.json()["id"])
        assert mov.tipo == "ENTRADA"
        assert mov.quantidade == 5
        assert mov.observacao == "Nota 123"
        assert mov.usuario == usuario
        assert mov.data_movimentacao is not None
        assert resposta.json()["usuario_nome"] == usuario.username


class TestSaida:
    def test_saida_diminui_o_estoque(self, api, criar_produto):
        produto = criar_produto(quantidade_estoque=10)

        resposta = movimentar(api, produto, "SAIDA", 4)

        assert resposta.status_code == 201
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 6

    def test_saida_de_todo_o_estoque(self, api, criar_produto):
        produto = criar_produto(quantidade_estoque=10)

        movimentar(api, produto, "SAIDA", 10)

        produto.refresh_from_db()
        assert produto.quantidade_estoque == 0

    def test_saida_maior_que_o_estoque_e_recusada_sem_efeitos(
        self, api, criar_produto
    ):
        produto = criar_produto(quantidade_estoque=3)

        resposta = movimentar(api, produto, "SAIDA", 4)

        assert resposta.status_code == 400
        assert "quantidade" in resposta.json()
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 3
        assert not MovimentacaoEstoque.objects.exists()


class TestValidacao:
    @pytest.mark.parametrize("quantidade", [0, -5])
    def test_quantidade_precisa_ser_positiva(self, api, produto, quantidade):
        resposta = movimentar(api, produto, "ENTRADA", quantidade)

        assert resposta.status_code == 400
        assert "quantidade" in resposta.json()

    def test_tipo_invalido_e_recusado(self, api, produto):
        resposta = movimentar(api, produto, "AJUSTE", 1)

        assert resposta.status_code == 400
        assert "tipo" in resposta.json()

    def test_produto_inexistente_e_recusado(self, api):
        resposta = api.post(
            URL,
            {"produto": 999999, "tipo": "ENTRADA", "quantidade": 1},
            format="json",
        )

        assert resposta.status_code == 400
        assert "produto" in resposta.json()

    def test_usuario_nao_pode_ser_forjado_pelo_cliente(
        self, api, usuario, outro_usuario, produto
    ):
        resposta = api.post(
            URL,
            {
                "produto": produto.id,
                "tipo": "ENTRADA",
                "quantidade": 1,
                "usuario": outro_usuario.id,
            },
            format="json",
        )

        mov = MovimentacaoEstoque.objects.get(id=resposta.json()["id"])
        assert mov.usuario == usuario


class TestHistorico:
    def test_movimentacoes_sucessivas_acumulam(self, api, criar_produto):
        produto = criar_produto(quantidade_estoque=0)

        movimentar(api, produto, "ENTRADA", 10)
        movimentar(api, produto, "SAIDA", 3)
        movimentar(api, produto, "ENTRADA", 5)

        produto.refresh_from_db()
        assert produto.quantidade_estoque == 12
        assert MovimentacaoEstoque.objects.count() == 3

    def test_lista_somente_as_movimentacoes_do_proprio_usuario(
        self, api, outro_usuario, produto
    ):
        movimentar(api, produto, "ENTRADA", 1, "minha")
        api_outro = APIClient()
        api_outro.force_login(outro_usuario)
        movimentar(api_outro, produto, "ENTRADA", 1, "do outro")

        observacoes = [m["observacao"] for m in api.get(URL).json()]

        assert observacoes == ["minha"]


class TestProdutoInativo:
    def test_movimentacao_em_produto_inativo_e_recusada(
        self, api, criar_produto
    ):
        produto = criar_produto(quantidade_estoque=10, ativo=False)

        resposta = movimentar(api, produto, "ENTRADA", 5)

        assert resposta.status_code == 400
        assert "inativo" in str(resposta.json()["produto"])
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 10
        assert not MovimentacaoEstoque.objects.exists()


class TestImutabilidade:
    """O histórico não pode ser reescrito; corrige-se com lançamento inverso."""

    @pytest.fixture
    def mov_id(self, api, criar_produto):
        self.produto = criar_produto(quantidade_estoque=0)
        return movimentar(api, self.produto, "ENTRADA", 10).json()["id"]

    @pytest.mark.parametrize("metodo", ["put", "patch"])
    def test_movimentacao_nao_pode_ser_editada(self, api, mov_id, metodo):
        resposta = getattr(api, metodo)(
            f"{URL}{mov_id}/", {"quantidade": 4}, format="json"
        )

        assert resposta.status_code == 405
        self.produto.refresh_from_db()
        assert self.produto.quantidade_estoque == 10
        assert MovimentacaoEstoque.objects.get(id=mov_id).quantidade == 10

    def test_movimentacao_nao_pode_ser_excluida(self, api, mov_id):
        resposta = api.delete(f"{URL}{mov_id}/")

        assert resposta.status_code == 405
        assert MovimentacaoEstoque.objects.filter(id=mov_id).exists()
        self.produto.refresh_from_db()
        assert self.produto.quantidade_estoque == 10

    def test_lancamento_errado_e_corrigido_com_movimentacao_inversa(
        self, api, mov_id
    ):
        movimentar(api, self.produto, "SAIDA", 6, "Estorno: entrada a maior")

        self.produto.refresh_from_db()
        assert self.produto.quantidade_estoque == 4
        assert MovimentacaoEstoque.objects.count() == 2


class TestConcorrencia:
    def test_trava_a_linha_do_produto_ao_movimentar(self, api, produto):
        with CaptureQueriesContext(connection) as consultas:
            movimentar(api, produto, "SAIDA", 1)

        assert any("FOR UPDATE" in q["sql"] for q in consultas)

    def test_saldo_e_relido_do_banco_e_nao_da_validacao(
        self, usuario, criar_produto
    ):
        """Simula a corrida de forma determinística: entre a validação e a
        gravação, outra transação consome o estoque."""
        produto = criar_produto(quantidade_estoque=10)
        serializer = MovimentacaoSerializer(
            data={"produto": produto.id, "tipo": "SAIDA", "quantidade": 8},
            context={"request": SimpleNamespace(user=usuario)},
        )
        assert serializer.is_valid(), serializer.errors

        Produto.objects.filter(id=produto.id).update(quantidade_estoque=5)

        with pytest.raises(ValidationError):
            serializer.save()
        produto.refresh_from_db()
        assert produto.quantidade_estoque == 5
        assert not MovimentacaoEstoque.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_saidas_simultaneas_nao_vendem_mais_que_o_estoque(
    usuario, criar_produto
):
    produto = criar_produto(quantidade_estoque=10)
    largada = threading.Barrier(2)
    status = []

    def vender():
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        try:
            largada.wait()
            status.append(movimentar(cliente, produto, "SAIDA", 6).status_code)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=vender) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(status) == [201, 400]
    produto.refresh_from_db()
    assert produto.quantidade_estoque == 4
    assert MovimentacaoEstoque.objects.count() == 1
