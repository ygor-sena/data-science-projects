from django.contrib import admin

from estoque.models import Categoria, MovimentacaoEstoque, Produto


def test_categoria_str_e_o_nome():
    assert str(Categoria(nome="Bebidas")) == "Bebidas"


def test_produto_str_e_o_nome():
    assert str(Produto(nome="Café 500g")) == "Café 500g"


def test_produto_novo_comeca_ativo_e_sem_estoque():
    produto = Produto(nome="Açúcar")

    assert produto.ativo is True
    assert produto.quantidade_estoque == 0
    assert produto.estoque_minimo == 0
    assert produto.data_validade is None


def test_movimentacao_aceita_apenas_entrada_e_saida():
    tipos = dict(MovimentacaoEstoque.TIPOS)
    assert set(tipos) == {"ENTRADA", "SAIDA"}


def test_admin_de_movimentacoes_e_somente_leitura():
    modelo_admin = admin.site._registry[MovimentacaoEstoque]

    assert not modelo_admin.has_add_permission(None)
    assert not modelo_admin.has_change_permission(None)
    assert not modelo_admin.has_delete_permission(None)
