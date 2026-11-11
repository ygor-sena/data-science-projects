from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Categoria, Produto, MovimentacaoEstoque
from .serializers import (
    CategoriaSerializer,
    ProdutoSerializer,
    MovimentacaoSerializer,
)
from .services import classificar_alertas


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


class ExclusaoProtegidaMixin:
    """Responde 409 em vez de 500 quando o registro tem dependentes."""
    mensagem_exclusao_protegida = ""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": self.mensagem_exclusao_protegida},
                status=status.HTTP_409_CONFLICT,
            )


class CategoriaViewSet(ExclusaoProtegidaMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    mensagem_exclusao_protegida = (
        "A categoria possui produtos vinculados e não pode ser excluída."
    )


class ProdutoViewSet(ExclusaoProtegidaMixin, viewsets.ModelViewSet):
    queryset = Produto.objects.select_related("categoria").filter(ativo=True)
    serializer_class = ProdutoSerializer
    mensagem_exclusao_protegida = (
        "O produto possui movimentações registradas e não pode ser "
        "excluído. Desative-o (ativo = false)."
    )

    @action(detail=False, methods=["get"])
    def alertas(self, request):
        alertas = classificar_alertas(
            self.get_queryset(), timezone.localdate()
        )

        return Response({
            chave: ProdutoSerializer(produtos, many=True).data
            for chave, produtos in alertas.items()
        })


class MovimentacaoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Movimentações são um histórico imutável: não há edição nem exclusão.
    Um lançamento errado é corrigido com uma movimentação inversa."""

    queryset = MovimentacaoEstoque.objects.select_related(
        "produto", "usuario"
    )
    serializer_class = MovimentacaoSerializer

    def get_queryset(self):
        return super().get_queryset().filter(
            usuario=self.request.user
        )
