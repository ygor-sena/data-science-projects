"""Jornadas completas pela pilha HTTP, com CSRF ativo como no navegador."""
import json
from datetime import timedelta

import pytest
from django.test import Client

from tests.conftest import SENHA

pytestmark = pytest.mark.django_db


@pytest.fixture
def navegador():
    return Client(enforce_csrf_checks=True)


def entrar(cliente, usuario, senha=SENHA):
    cliente.get("/login/")
    return cliente.post("/login/", {
        "username": usuario.username,
        "password": senha,
        "csrfmiddlewaretoken": cliente.cookies["csrftoken"].value,
    })


def enviar(cliente, url, dados):
    return cliente.post(
        url,
        json.dumps(dados),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
    )


def test_visitante_e_redirecionado_para_o_login(navegador):
    resposta = navegador.get("/")

    assert resposta.status_code == 302
    assert resposta.url.startswith("/login/")


def test_login_invalido_mostra_mensagem_de_erro(navegador, usuario):
    resposta = entrar(navegador, usuario, senha="errada")

    assert resposta.status_code == 200
    assert "Usuário ou senha inválidos" in resposta.content.decode()


def test_login_logout(navegador, usuario):
    resposta = entrar(navegador, usuario)
    assert resposta.status_code == 302
    assert resposta.url == "/"

    dashboard = navegador.get("/")
    assert dashboard.status_code == 200
    assert usuario.username in dashboard.content.decode()

    navegador.post("/logout/", {
        "csrfmiddlewaretoken": navegador.cookies["csrftoken"].value
    })
    assert navegador.get("/").status_code == 302


def test_api_recusa_escrita_sem_token_csrf(navegador, usuario):
    entrar(navegador, usuario)

    resposta = navegador.post(
        "/api/categorias/",
        json.dumps({"nome": "Bebidas"}),
        content_type="application/json",
    )

    assert resposta.status_code == 403


def test_jornada_completa_do_estoque(navegador, usuario, hoje):
    entrar(navegador, usuario)

    categoria = enviar(navegador, "/api/categorias/", {"nome": "Laticínios"})
    assert categoria.status_code == 201

    produto = enviar(navegador, "/api/produtos/", {
        "nome": "Iogurte",
        "categoria": categoria.json()["id"],
        "preco": "3.50",
        "quantidade_estoque": 0,
        "estoque_minimo": 5,
        "data_validade": str(hoje + timedelta(days=7)),
    })
    assert produto.status_code == 201
    produto_id = produto.json()["id"]

    alertas = navegador.get("/api/produtos/alertas/").json()
    assert [p["id"] for p in alertas["sem_estoque"]] == [produto_id]

    entrada = enviar(navegador, "/api/movimentacoes/", {
        "produto": produto_id, "tipo": "ENTRADA", "quantidade": 20,
    })
    assert entrada.status_code == 201

    saida = enviar(navegador, "/api/movimentacoes/", {
        "produto": produto_id, "tipo": "SAIDA", "quantidade": 17,
    })
    assert saida.status_code == 201

    saida_excessiva = enviar(navegador, "/api/movimentacoes/", {
        "produto": produto_id, "tipo": "SAIDA", "quantidade": 99,
    })
    assert saida_excessiva.status_code == 400

    estoque = navegador.get(f"/api/produtos/{produto_id}/").json()
    assert estoque["quantidade_estoque"] == 3

    alertas = navegador.get("/api/produtos/alertas/").json()
    assert alertas["sem_estoque"] == []
    assert [p["id"] for p in alertas["estoque_baixo"]] == [produto_id]
    assert [p["id"] for p in alertas["proximos_vencimento"]] == [produto_id]

    historico = navegador.get("/api/movimentacoes/").json()
    assert [m["tipo"] for m in historico] == ["SAIDA", "ENTRADA"]
