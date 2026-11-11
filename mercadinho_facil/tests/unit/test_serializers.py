from datetime import date
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from estoque.models import Categoria, MovimentacaoEstoque, Produto
from estoque.serializers import MovimentacaoSerializer, ProdutoSerializer


def produto_em_memoria(quantidade=10):
    return Produto(id=1, nome="Feijão", quantidade_estoque=quantidade)


class TestMovimentacaoSerializerValidate:
    def validar(self, tipo, quantidade, estoque=10):
        attrs = {
            "produto": produto_em_memoria(estoque),
            "tipo": tipo,
            "quantidade": quantidade,
        }
        return MovimentacaoSerializer().validate(attrs)

    def test_entrada_valida_e_aceita(self):
        attrs = self.validar(MovimentacaoEstoque.ENTRADA, 5)
        assert attrs["quantidade"] == 5

    def test_saida_dentro_do_estoque_e_aceita(self):
        attrs = self.validar(MovimentacaoEstoque.SAIDA, 10, estoque=10)
        assert attrs["quantidade"] == 10

    def test_saida_acima_do_estoque_retorna_erro_no_campo_quantidade(self):
        with pytest.raises(ValidationError) as erro:
            self.validar(MovimentacaoEstoque.SAIDA, 11, estoque=10)

        assert "estoque disponível" in str(erro.value.detail["quantidade"])

    def test_quantidade_zero_retorna_erro_no_campo_quantidade(self):
        with pytest.raises(ValidationError) as erro:
            self.validar(MovimentacaoEstoque.ENTRADA, 0)

        assert "maior que zero" in str(erro.value.detail["quantidade"])

    def test_produto_inativo_retorna_erro_no_campo_produto(self):
        produto = produto_em_memoria(10)
        produto.ativo = False
        attrs = {
            "produto": produto,
            "tipo": MovimentacaoEstoque.ENTRADA,
            "quantidade": 1,
        }

        with pytest.raises(ValidationError) as erro:
            MovimentacaoSerializer().validate(attrs)

        assert "inativo" in str(erro.value.detail["produto"])

    def test_validacao_nao_altera_o_estoque_do_produto(self):
        attrs = {
            "produto": produto_em_memoria(10),
            "tipo": MovimentacaoEstoque.SAIDA,
            "quantidade": 4,
        }
        MovimentacaoSerializer().validate(attrs)
        assert attrs["produto"].quantidade_estoque == 10


class TestProdutoSerializerRepresentacao:
    def test_inclui_nome_da_categoria(self):
        produto = Produto(
            id=7,
            nome="Leite",
            categoria=Categoria(id=2, nome="Laticínios"),
            preco=Decimal("4.99"),
            quantidade_estoque=12,
            estoque_minimo=4,
            data_validade=date(2026, 12, 1),
        )

        dados = ProdutoSerializer(produto).data

        assert dados["categoria"] == 2
        assert dados["categoria_nome"] == "Laticínios"
        assert dados["preco"] == "4.99"
        assert dados["data_validade"] == "2026-12-01"


class TestProdutoSerializerPreco:
    @pytest.mark.parametrize("preco", ["0", "0.00", "19.90"])
    def test_aceita_preco_zero_ou_positivo(self, preco):
        campo = ProdutoSerializer().fields["preco"]
        assert campo.run_validation(preco) == Decimal(preco)

    @pytest.mark.parametrize("preco", ["-0.01", "-10"])
    def test_recusa_preco_negativo(self, preco):
        campo = ProdutoSerializer().fields["preco"]
        with pytest.raises(ValidationError):
            campo.run_validation(preco)


class TestMovimentacaoSerializerCampos:
    def test_usuario_e_data_sao_somente_leitura(self):
        campos = MovimentacaoSerializer().fields
        assert campos["usuario_nome"].read_only
        assert campos["data_movimentacao"].read_only
        assert "usuario" not in campos
