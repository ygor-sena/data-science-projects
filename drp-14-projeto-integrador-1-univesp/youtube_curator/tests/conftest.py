import pytest
from django.contrib.auth.models import User
from curator.models import TrainingModule, CuratedVideo


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="funcionario", password="senha123", first_name="Bruno"
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="gerente", password="senha123", is_staff=True
    )


@pytest.fixture
def module(db, user):
    return TrainingModule.objects.create(
        name="Técnicas de Venda",
        slug="tecnicas-venda",
        description="Aprenda a vender mais.",
        default_keywords="técnicas de venda,como vender",
        icon="bi-graph-up-arrow",
        created_by=user,
    )


@pytest.fixture
def video(db, module, user):
    return CuratedVideo.objects.create(
        youtube_id="dQw4w9WgXcQ",
        title="Como Vender Queijo Mineiro",
        description="Dicas de vendas para produtos artesanais.",
        thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
        channel_name="Canal Teste",
        duration="5:30",
        module=module,
        added_by=user,
    )
