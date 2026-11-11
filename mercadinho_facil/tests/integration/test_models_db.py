import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from estoque.models import Categoria, MovimentacaoEstoque, Produto

pytestmark = pytest.mark.django_db


def test_nome_da_categoria_e_unico(categoria):
    with pytest.raises(IntegrityError):
        Categoria.objects.create(nome=categoria.nome)


def test_categoria_com_produtos_nao_pode_ser_excluida(produto):
    with pytest.raises(ProtectedError):
        produto.categoria.delete()


def test_produto_com_movimentacoes_nao_pode_ser_excluido(produto, usuario):
    MovimentacaoEstoque.objects.create(
        produto=produto, tipo="ENTRADA", quantidade=1, usuario=usuario
    )
    with pytest.raises(ProtectedError):
        produto.delete()


def test_banco_recusa_preco_negativo_mesmo_fora_da_api(criar_produto):
    with pytest.raises(IntegrityError):
        criar_produto(preco=-1)


def test_categorias_sao_ordenadas_por_nome():
    for nome in ["Limpeza", "Bebidas", "Hortifruti"]:
        Categoria.objects.create(nome=nome)

    nomes = list(Categoria.objects.values_list("nome", flat=True))

    assert nomes == ["Bebidas", "Hortifruti", "Limpeza"]


def test_produtos_sao_ordenados_por_nome(criar_produto):
    criar_produto(nome="Sabão")
    criar_produto(nome="Arroz")

    assert [p.nome for p in Produto.objects.all()] == ["Arroz", "Sabão"]


def test_data_de_cadastro_e_preenchida_automaticamente(produto):
    assert produto.data_cadastro is not None
