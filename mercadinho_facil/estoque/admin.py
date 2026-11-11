from django.contrib import admin
from .models import Categoria, Produto, MovimentacaoEstoque

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = [
        "nome", "categoria", "quantidade_estoque",
        "estoque_minimo", "data_validade", "ativo"
    ]
    list_filter = ["categoria", "ativo"]
    search_fields = ["nome"]


@admin.register(MovimentacaoEstoque)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = [
        "produto", "tipo", "quantidade",
        "data_movimentacao", "usuario"
    ]
    list_filter = ["tipo"]

    # Somente leitura: movimentações passam pela API, que atualiza o estoque.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
