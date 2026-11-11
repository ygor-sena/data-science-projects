from datetime import timedelta
from decimal import Decimal

import pytest

from estoque.models import Produto

pytestmark = pytest.mark.django_db

URL = "/api/produtos/"


@pytest.fixture
def dados_produto(categoria):
    return {
        "nome": "Feijão 1kg",
        "categoria": categoria.id,
        "preco": "8.49",
        "quantidade_estoque": 20,
        "estoque_minimo": 5,
        "data_validade": "2027-01-31",
    }


class TestCadastro:
    def test_cadastra_produto_com_todos_os_campos(self, api, dados_produto):
        resposta = api.post(URL, dados_produto, format="json")

        assert resposta.status_code == 201
        produto = Produto.objects.get(id=resposta.json()["id"])
        assert produto.nome == "Feijão 1kg"
        assert produto.preco == Decimal("8.49")
        assert produto.quantidade_estoque == 20
        assert produto.estoque_minimo == 5
        assert str(produto.data_validade) == "2027-01-31"
        assert produto.ativo is True

    def test_data_de_validade_e_opcional(self, api, dados_produto):
        dados_produto["data_validade"] = None

        resposta = api.post(URL, dados_produto, format="json")

        assert resposta.status_code == 201
        assert resposta.json()["data_validade"] is None

    def test_preco_zero_e_aceito(self, api, dados_produto):
        dados_produto["preco"] = "0.00"

        assert api.post(URL, dados_produto, format="json").status_code == 201

    def test_alteracao_para_preco_negativo_e_recusada(self, api, produto):
        resposta = api.patch(
            f"{URL}{produto.id}/", {"preco": "-1.00"}, format="json"
        )

        assert resposta.status_code == 400
        produto.refresh_from_db()
        assert produto.preco == Decimal("25.90")

    @pytest.mark.parametrize("campo", ["nome", "categoria", "preco"])
    def test_campos_obrigatorios(self, api, dados_produto, campo):
        del dados_produto[campo]

        resposta = api.post(URL, dados_produto, format="json")

        assert resposta.status_code == 400
        assert campo in resposta.json()

    @pytest.mark.parametrize(
        "campo, valor",
        [
            ("quantidade_estoque", -1),
            ("estoque_minimo", -1),
            ("preco", "-0.01"),
            ("preco", "abc"),
            ("preco", "123456789.00"),  # excede max_digits=10
            ("data_validade", "31/01/2027"),
            ("categoria", 999999),
        ],
    )
    def test_recusa_valores_invalidos(self, api, dados_produto, campo, valor):
        dados_produto[campo] = valor

        resposta = api.post(URL, dados_produto, format="json")

        assert resposta.status_code == 400
        assert campo in resposta.json()
        assert not Produto.objects.exists()


class TestConsulta:
    def test_lista_inclui_nome_da_categoria(self, api, produto):
        item = api.get(URL).json()[0]

        assert item["nome"] == produto.nome
        assert item["categoria_nome"] == produto.categoria.nome

    def test_lista_somente_produtos_ativos(self, api, criar_produto):
        criar_produto(nome="Ativo")
        criar_produto(nome="Inativo", ativo=False)

        nomes = [p["nome"] for p in api.get(URL).json()]

        assert nomes == ["Ativo"]

    def test_produto_inativo_nao_e_encontrado_no_detalhe(
        self, api, criar_produto
    ):
        inativo = criar_produto(ativo=False)

        assert api.get(f"{URL}{inativo.id}/").status_code == 404

    def test_detalhe_do_produto(self, api, produto):
        resposta = api.get(f"{URL}{produto.id}/")

        assert resposta.status_code == 200
        assert resposta.json()["id"] == produto.id


class TestAlteracao:
    def test_atualiza_preco_e_estoque_minimo(self, api, produto):
        resposta = api.patch(
            f"{URL}{produto.id}/",
            {"preco": "30.00", "estoque_minimo": 8},
            format="json",
        )

        assert resposta.status_code == 200
        produto.refresh_from_db()
        assert produto.preco == Decimal("30.00")
        assert produto.estoque_minimo == 8

    def test_desativar_remove_o_produto_da_listagem(self, api, produto):
        api.patch(f"{URL}{produto.id}/", {"ativo": False}, format="json")

        assert api.get(URL).json() == []

    def test_exclui_produto_sem_movimentacoes(self, api, produto):
        assert api.delete(f"{URL}{produto.id}/").status_code == 204
        assert not Produto.objects.exists()

    def test_excluir_produto_com_movimentacoes_retorna_conflito(
        self, api, produto
    ):
        api.post(
            "/api/movimentacoes/",
            {"produto": produto.id, "tipo": "ENTRADA", "quantidade": 1},
            format="json",
        )

        resposta = api.delete(f"{URL}{produto.id}/")

        assert resposta.status_code == 409
        assert "Desative" in resposta.json()["detail"]
        assert Produto.objects.filter(id=produto.id).exists()


class TestAlertas:
    URL = "/api/produtos/alertas/"

    def nomes(self, resposta, chave):
        return [p["nome"] for p in resposta.json()[chave]]

    def test_retorna_as_quatro_listas_de_alerta(self, api):
        assert set(api.get(self.URL).json()) == {
            "estoque_baixo",
            "sem_estoque",
            "proximos_vencimento",
            "vencidos",
        }

    def test_classifica_produtos_por_alerta(self, api, criar_produto, hoje):
        criar_produto(nome="Normal")
        criar_produto(nome="Baixo", quantidade_estoque=2, estoque_minimo=5)
        criar_produto(nome="Zerado", quantidade_estoque=0)
        criar_produto(
            nome="Vencendo", data_validade=hoje + timedelta(days=10)
        )
        criar_produto(nome="Vencido", data_validade=hoje - timedelta(days=1))

        resposta = api.get(self.URL)

        assert resposta.status_code == 200
        assert self.nomes(resposta, "estoque_baixo") == ["Baixo"]
        assert self.nomes(resposta, "sem_estoque") == ["Zerado"]
        assert self.nomes(resposta, "proximos_vencimento") == ["Vencendo"]
        assert self.nomes(resposta, "vencidos") == ["Vencido"]

    def test_ignora_produtos_inativos(self, api, criar_produto):
        criar_produto(quantidade_estoque=0, ativo=False)

        assert api.get(self.URL).json()["sem_estoque"] == []
