from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, ProdutoViewSet, MovimentacaoViewSet

router = DefaultRouter()
router.register("categorias", CategoriaViewSet)
router.register("produtos", ProdutoViewSet)
router.register("movimentacoes", MovimentacaoViewSet)

urlpatterns = router.urls
