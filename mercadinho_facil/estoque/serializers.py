from django.db import transaction
from rest_framework import serializers
from .models import Categoria, Produto, MovimentacaoEstoque
from .services import calcular_novo_estoque


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome"]


class ProdutoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(
        source="categoria.nome",
        read_only=True
    )

    class Meta:
        model = Produto
        fields = [
            "id", "nome", "categoria", "categoria_nome",
            "preco", "quantidade_estoque", "estoque_minimo",
            "data_validade", "data_cadastro", "ativo"
        ]


class MovimentacaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            "id", "produto", "tipo", "quantidade",
            "data_movimentacao", "observacao", "usuario_nome"
        ]
        read_only_fields = [
            "id", "data_movimentacao", "usuario_nome"
        ]

    @staticmethod
    def _novo_estoque(produto, tipo, quantidade):
        if not produto.ativo:
            raise serializers.ValidationError(
                {"produto": "Não é possível movimentar um produto inativo."}
            )
        try:
            return calcular_novo_estoque(
                produto.quantidade_estoque, tipo, quantidade
            )
        except ValueError as erro:
            raise serializers.ValidationError({"quantidade": str(erro)})

    def validate(self, attrs):
        self._novo_estoque(
            attrs["produto"], attrs["tipo"], attrs["quantidade"]
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        # Relê o produto travando a linha até o fim da transação: duas
        # movimentações simultâneas não podem partir do mesmo saldo.
        produto = Produto.objects.select_for_update().get(
            pk=validated_data["produto"].pk
        )
        produto.quantidade_estoque = self._novo_estoque(
            produto, validated_data["tipo"], validated_data["quantidade"]
        )
        produto.save(update_fields=["quantidade_estoque"])
        validated_data["produto"] = produto

        return MovimentacaoEstoque.objects.create(
            usuario=request.user,
            **validated_data
        )
