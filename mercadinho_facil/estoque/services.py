"""Regras de negócio puras do estoque (sem acesso a banco ou HTTP)."""
from datetime import timedelta

DIAS_AVISO_VENCIMENTO = 30

ENTRADA = "ENTRADA"
SAIDA = "SAIDA"


class EstoqueInsuficiente(ValueError):
    pass


def calcular_novo_estoque(atual, tipo, quantidade):
    if quantidade <= 0:
        raise ValueError("Informe uma quantidade maior que zero.")

    if tipo == ENTRADA:
        return atual + quantidade

    if tipo == SAIDA:
        if quantidade > atual:
            raise EstoqueInsuficiente(
                "A saída não pode ser maior que o estoque disponível."
            )
        return atual - quantidade

    raise ValueError(f"Tipo de movimentação inválido: {tipo}")


def estoque_baixo(produto):
    return 0 < produto.quantidade_estoque <= produto.estoque_minimo


def sem_estoque(produto):
    return produto.quantidade_estoque == 0


def proximo_vencimento(produto, hoje, dias=DIAS_AVISO_VENCIMENTO):
    return bool(
        produto.data_validade
        and hoje <= produto.data_validade <= hoje + timedelta(days=dias)
    )


def vencido(produto, hoje):
    return bool(produto.data_validade and produto.data_validade < hoje)


def classificar_alertas(produtos, hoje):
    produtos = list(produtos)
    return {
        "estoque_baixo": [p for p in produtos if estoque_baixo(p)],
        "sem_estoque": [p for p in produtos if sem_estoque(p)],
        "proximos_vencimento": [
            p for p in produtos if proximo_vencimento(p, hoje)
        ],
        "vencidos": [p for p in produtos if vencido(p, hoje)],
    }
