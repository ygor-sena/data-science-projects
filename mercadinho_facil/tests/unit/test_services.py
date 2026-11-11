from datetime import date, timedelta

import pytest

from estoque.models import Produto
from estoque.services import (
    DIAS_AVISO_VENCIMENTO,
    ENTRADA,
    SAIDA,
    EstoqueInsuficiente,
    calcular_novo_estoque,
    classificar_alertas,
    estoque_baixo,
    proximo_vencimento,
    sem_estoque,
    vencido,
)

HOJE = date(2026, 6, 15)


def produto(quantidade=10, minimo=3, validade=None, nome="Produto"):
    """Produto em memória: nunca é salvo, então o teste não usa o banco."""
    return Produto(
        nome=nome,
        quantidade_estoque=quantidade,
        estoque_minimo=minimo,
        data_validade=validade,
    )


class TestCalcularNovoEstoque:
    def test_entrada_soma_a_quantidade(self):
        assert calcular_novo_estoque(10, ENTRADA, 5) == 15

    def test_entrada_em_produto_sem_estoque(self):
        assert calcular_novo_estoque(0, ENTRADA, 7) == 7

    def test_saida_subtrai_a_quantidade(self):
        assert calcular_novo_estoque(10, SAIDA, 4) == 6

    def test_saida_de_todo_o_estoque_zera_o_produto(self):
        assert calcular_novo_estoque(10, SAIDA, 10) == 0

    def test_saida_maior_que_o_estoque_e_recusada(self):
        with pytest.raises(EstoqueInsuficiente, match="estoque disponível"):
            calcular_novo_estoque(10, SAIDA, 11)

    def test_saida_de_produto_sem_estoque_e_recusada(self):
        with pytest.raises(EstoqueInsuficiente):
            calcular_novo_estoque(0, SAIDA, 1)

    @pytest.mark.parametrize("tipo", [ENTRADA, SAIDA])
    @pytest.mark.parametrize("quantidade", [0, -1])
    def test_quantidade_precisa_ser_positiva(self, tipo, quantidade):
        with pytest.raises(ValueError, match="maior que zero"):
            calcular_novo_estoque(10, tipo, quantidade)

    def test_tipo_desconhecido_e_recusado(self):
        with pytest.raises(ValueError, match="inválido"):
            calcular_novo_estoque(10, "AJUSTE", 1)


class TestEstoqueBaixo:
    @pytest.mark.parametrize(
        "quantidade, minimo, esperado",
        [
            (1, 3, True),    # abaixo do mínimo
            (3, 3, True),    # exatamente no mínimo
            (4, 3, False),   # acima do mínimo
            (0, 3, False),   # zerado é "sem estoque", não "baixo"
            (5, 0, False),   # sem mínimo definido
        ],
    )
    def test_limites(self, quantidade, minimo, esperado):
        assert estoque_baixo(produto(quantidade, minimo)) is esperado


class TestSemEstoque:
    @pytest.mark.parametrize(
        "quantidade, esperado", [(0, True), (1, False), (50, False)]
    )
    def test_somente_quantidade_zero(self, quantidade, esperado):
        assert sem_estoque(produto(quantidade)) is esperado


class TestValidade:
    @pytest.mark.parametrize(
        "dias, esperado",
        [
            (-1, False),                         # já venceu
            (0, True),                           # vence hoje
            (DIAS_AVISO_VENCIMENTO, True),       # último dia da janela
            (DIAS_AVISO_VENCIMENTO + 1, False),  # fora da janela
        ],
    )
    def test_proximo_vencimento(self, dias, esperado):
        p = produto(validade=HOJE + timedelta(days=dias))
        assert proximo_vencimento(p, HOJE) is esperado

    @pytest.mark.parametrize(
        "dias, esperado", [(-30, True), (-1, True), (0, False), (1, False)]
    )
    def test_vencido(self, dias, esperado):
        p = produto(validade=HOJE + timedelta(days=dias))
        assert vencido(p, HOJE) is esperado

    def test_produto_sem_validade_nunca_gera_alerta(self):
        p = produto(validade=None)
        assert not proximo_vencimento(p, HOJE)
        assert not vencido(p, HOJE)


class TestClassificarAlertas:
    def test_lista_vazia_retorna_todas_as_chaves_vazias(self):
        assert classificar_alertas([], HOJE) == {
            "estoque_baixo": [],
            "sem_estoque": [],
            "proximos_vencimento": [],
            "vencidos": [],
        }

    def test_distribui_cada_produto_na_categoria_correta(self):
        normal = produto(10, 3, HOJE + timedelta(days=200), "Normal")
        baixo = produto(2, 3, None, "Baixo")
        zerado = produto(0, 3, None, "Zerado")
        vencendo = produto(10, 3, HOJE + timedelta(days=5), "Vencendo")
        venceu = produto(10, 3, HOJE - timedelta(days=5), "Venceu")

        alertas = classificar_alertas(
            [normal, baixo, zerado, vencendo, venceu], HOJE
        )

        assert alertas["estoque_baixo"] == [baixo]
        assert alertas["sem_estoque"] == [zerado]
        assert alertas["proximos_vencimento"] == [vencendo]
        assert alertas["vencidos"] == [venceu]

    def test_um_produto_pode_aparecer_em_mais_de_um_alerta(self):
        critico = produto(0, 3, HOJE - timedelta(days=1))

        alertas = classificar_alertas([critico], HOJE)

        assert alertas["sem_estoque"] == [critico]
        assert alertas["vencidos"] == [critico]

    def test_aceita_qualquer_iteravel(self):
        p = produto(0)
        alertas = classificar_alertas(iter([p]), HOJE)
        assert alertas["sem_estoque"] == [p]
