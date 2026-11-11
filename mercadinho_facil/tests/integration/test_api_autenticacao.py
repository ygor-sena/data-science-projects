import pytest

pytestmark = pytest.mark.django_db

ENDPOINTS = [
    "/api/categorias/",
    "/api/produtos/",
    "/api/produtos/alertas/",
    "/api/movimentacoes/",
]


@pytest.mark.parametrize("url", ENDPOINTS)
def test_api_exige_login_para_leitura(api_anonima, url):
    assert api_anonima.get(url).status_code == 403


@pytest.mark.parametrize(
    "url", ["/api/categorias/", "/api/produtos/", "/api/movimentacoes/"]
)
def test_api_exige_login_para_escrita(api_anonima, url):
    assert api_anonima.post(url, {}, format="json").status_code == 403


@pytest.mark.parametrize("url", ENDPOINTS)
def test_usuario_logado_acessa_a_api(api, url):
    assert api.get(url).status_code == 200
