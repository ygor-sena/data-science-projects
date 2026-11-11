import pytest

from estoque.models import Categoria

pytestmark = pytest.mark.django_db

URL = "/api/categorias/"


def test_cadastra_categoria(api):
    resposta = api.post(URL, {"nome": "Bebidas"}, format="json")

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Bebidas"
    assert Categoria.objects.filter(nome="Bebidas").exists()


def test_lista_categorias_em_ordem_alfabetica(api):
    Categoria.objects.create(nome="Limpeza")
    Categoria.objects.create(nome="Bebidas")

    nomes = [c["nome"] for c in api.get(URL).json()]

    assert nomes == ["Bebidas", "Limpeza"]


def test_recusa_categoria_duplicada(api, categoria):
    resposta = api.post(URL, {"nome": categoria.nome}, format="json")

    assert resposta.status_code == 400
    assert "nome" in resposta.json()


def test_recusa_categoria_sem_nome(api):
    resposta = api.post(URL, {"nome": ""}, format="json")

    assert resposta.status_code == 400
    assert "nome" in resposta.json()


def test_renomeia_categoria(api, categoria):
    resposta = api.patch(
        f"{URL}{categoria.id}/", {"nome": "Mercearia"}, format="json"
    )

    assert resposta.status_code == 200
    categoria.refresh_from_db()
    assert categoria.nome == "Mercearia"


def test_exclui_categoria_sem_produtos(api, categoria):
    resposta = api.delete(f"{URL}{categoria.id}/")

    assert resposta.status_code == 204
    assert not Categoria.objects.exists()


def test_excluir_categoria_com_produtos_retorna_conflito(api, produto):
    resposta = api.delete(f"{URL}{produto.categoria.id}/")

    assert resposta.status_code == 409
    assert "produtos vinculados" in resposta.json()["detail"]
    assert Categoria.objects.filter(id=produto.categoria.id).exists()
