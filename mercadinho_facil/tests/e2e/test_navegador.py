"""Testes no navegador real (Playwright): validam o JavaScript do dashboard.

Requer: pip install playwright && python -m playwright install chromium
Sem o Playwright instalado, estes testes são ignorados (skip).
"""
import os

import pytest
from django.db import connections

from tests.conftest import SENHA

# O Playwright síncrono roda um event loop na thread do teste; isso libera
# o ORM do Django para preparar os dados mesmo assim.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def pagina():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as erro:
            pytest.skip(f"Chromium do Playwright indisponível: {erro}")
        page = browser.new_page()
        # Não depender de rede externa: o widget VLibras é bloqueado.
        page.route("**/vlibras.gov.br/**", lambda rota: rota.abort())
        page.on("dialog", lambda dialogo: dialogo.accept())
        page.set_default_timeout(10_000)
        yield page
        browser.close()
        # Enquanto o Playwright está ativo, o Django guarda a conexão do
        # teste em outro contexto; fechá-la aqui evita uma sessão órfã que
        # impede a remoção do banco de testes.
        connections.close_all()


@pytest.fixture
def logado(pagina, live_server, usuario):
    pagina.goto(f"{live_server.url}/login/")
    pagina.get_by_label("Usuário").fill(usuario.username)
    pagina.get_by_label("Senha").fill(SENHA)
    pagina.get_by_role("button", name="Entrar").click()
    pagina.wait_for_url(f"{live_server.url}/")
    return pagina


def linha_do_produto(pagina, nome):
    return pagina.locator("#tabelaProdutos tr", has_text=nome)


def test_cadastrar_produto_e_movimentar_estoque_pela_interface(logado):
    pagina = logado

    pagina.get_by_label("Nome").fill("Café 500g")
    pagina.get_by_label("Categoria").fill("Mercearia")
    pagina.get_by_label("Preço").fill("18.90")
    pagina.get_by_label("Quantidade inicial").fill("10")
    pagina.get_by_label("Estoque mínimo").fill("3")
    pagina.get_by_role("button", name="Cadastrar produto").click()

    linha = linha_do_produto(pagina, "Café 500g")
    linha.wait_for()
    assert "Mercearia" in linha.inner_text()
    assert "Normal" in linha.inner_text()
    assert pagina.locator("#totalProdutos").inner_text() == "1"

    pagina.locator("#movTipo").select_option("SAIDA")
    pagina.locator("#movQuantidade").fill("8")
    pagina.get_by_role("button", name="Registrar movimentação").click()

    mensagem = pagina.locator("#mensagem")
    mensagem.filter(has_text="sucesso").wait_for()
    linha.filter(has_text="Estoque baixo").wait_for()
    assert pagina.locator("#estoqueBaixo").inner_text() == "1"


def test_saida_maior_que_o_estoque_mostra_erro(logado, produto):
    pagina = logado
    pagina.reload()
    linha_do_produto(pagina, produto.nome).wait_for()

    pagina.locator("#movTipo").select_option("SAIDA")
    pagina.locator("#movQuantidade").fill(str(produto.quantidade_estoque + 1))
    pagina.get_by_role("button", name="Registrar movimentação").click()

    pagina.locator("#mensagem").filter(
        has_text="Verifique o estoque"
    ).wait_for()
    produto.refresh_from_db()
    assert produto.quantidade_estoque == 10


def test_busca_filtra_a_tabela(logado, criar_produto):
    criar_produto(nome="Arroz")
    criar_produto(nome="Feijão")
    pagina = logado
    pagina.reload()
    linha_do_produto(pagina, "Arroz").wait_for()

    pagina.get_by_label("Buscar produto").fill("fei")

    linhas = pagina.locator("#tabelaProdutos tr")
    assert linhas.count() == 1
    assert "Feijão" in linhas.first.inner_text()
