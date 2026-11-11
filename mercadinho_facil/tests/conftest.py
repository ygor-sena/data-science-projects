from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from estoque.models import Categoria, Produto

SENHA = "senha-de-teste-123"


def pytest_collection_modifyitems(items):
    """Marca cada teste com a camada da pirâmide pela pasta onde está."""
    for item in items:
        camada = Path(item.fspath).parent.name
        if camada in ("unit", "integration", "e2e"):
            item.add_marker(getattr(pytest.mark, camada))


@pytest.fixture
def hoje():
    return timezone.localdate()


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user(
        username="operador", password=SENHA
    )


@pytest.fixture
def outro_usuario(db):
    return get_user_model().objects.create_user(
        username="outro", password=SENHA
    )


@pytest.fixture
def api(usuario):
    client = APIClient()
    client.force_login(usuario)
    return client


@pytest.fixture
def api_anonima():
    return APIClient()


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Alimentos")


@pytest.fixture
def criar_produto(categoria):
    """Fábrica de produtos: só informe o que importa para o teste."""
    def _criar(**campos):
        dados = {
            "nome": "Arroz 5kg",
            "categoria": categoria,
            "preco": Decimal("25.90"),
            "quantidade_estoque": 10,
            "estoque_minimo": 3,
            "data_validade": timezone.localdate() + timedelta(days=180),
        }
        dados.update(campos)
        return Produto.objects.create(**dados)
    return _criar


@pytest.fixture
def produto(criar_produto):
    return criar_produto()
