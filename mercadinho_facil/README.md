# Mercadinho Fácil — Quinzena 5

Base inicial de desenvolvimento do MVP do Projeto Integrador.

## Stack
- Django
- Django REST Framework
- PostgreSQL
- HTML + CSS + JavaScript
- Git/GitHub (controle de versões)

## Funcionalidades desta versão
- Login do usuário
- Cadastro de categorias
- Cadastro de produtos
- Consulta/pesquisa de estoque
- Registro de entrada
- Registro de saída
- Atualização automática do estoque
- Estoque mínimo
- Produtos sem estoque
- Controle de validade
- Produtos próximos do vencimento
- Produtos vencidos
- API REST

## 1. Criar ambiente
python -m venv .venv

Windows:
.venv\Scripts\activate

Linux/macOS:
source .venv/bin/activate

## 2. Instalar dependências
pip install -r requirements.txt

## 3. Criar banco PostgreSQL
Crie um banco chamado `mercadinho_facil`.

Exemplo:
CREATE DATABASE mercadinho_facil;

## 4. Configurar ambiente
Copie `.env.example` para `.env` e informe usuário/senha do PostgreSQL.

## 5. Criar tabelas Django
python manage.py makemigrations
python manage.py migrate

## 6. Criar usuário para entrar no sistema
python manage.py createsuperuser

## 7. Executar
python manage.py runserver

Abra:
http://127.0.0.1:8000/

API:
http://127.0.0.1:8000/api/produtos/
http://127.0.0.1:8000/api/categorias/
http://127.0.0.1:8000/api/movimentacoes/
http://127.0.0.1:8000/api/produtos/alertas/

## 8. Testes automatizados
Os testes seguem a pirâmide de testes (Martin Fowler): muitos testes
rápidos na base, poucos testes lentos no topo.

| Camada | Pasta | O que testa | Banco |
|---|---|---|---|
| Unitário | `tests/unit/` | Regras de estoque e alertas (`estoque/services.py`), validação dos serializers | Não |
| Integração | `tests/integration/` | Restrições do banco e todos os endpoints da API | PostgreSQL |
| E2E | `tests/e2e/` | Jornadas do usuário: login, CSRF, cadastro, movimentação; navegador real com Playwright | PostgreSQL |

Instalar dependências de desenvolvimento:

    pip install -r requirements-dev.txt
    python -m playwright install chromium

Executar:

    pytest                    # todos
    pytest -m unit            # só a base da pirâmide (menos de 1 s)
    pytest -m integration
    pytest -m e2e
    pytest --cov=estoque --cov-report=term-missing

O usuário do PostgreSQL configurado no `.env` precisa ter permissão para
criar bancos, pois o pytest cria e remove o banco `test_mercadinho_facil`.
Os testes de navegador são ignorados se o Playwright não estiver instalado.

Testes marcados como `xfail` documentam bugs conhecidos; quando o bug for
corrigido, o teste passa a falhar como "XPASS" e o marcador deve ser removido.

## 9. Deploy na nuvem (Azure App Service)

O sistema está publicado em **https://mercadinho-facil.azurewebsites.net**.

### Arquitetura

| Recurso | Nome | Região | Plano |
|---|---|---|---|
| Grupo de recursos | `mercadinho-rg` | Brazil South | — |
| Banco PostgreSQL 16 (Flexible Server) | `mercadinho-pg-ygor` | Brazil South | Burstable B1ms, 32 GB |
| Plano do App Service (Linux) | `mercadinho-plan` | West US 3 | B1 |
| Aplicação web (Python 3.12) | `mercadinho-facil` | West US 3 | — |

Arquivos do projeto usados no deploy:

- `startup.sh`: executado a cada inicialização do app. Roda `collectstatic`,
  `migrate` e `criar_admin`, depois inicia o gunicorn. Precisa ter quebras de
  linha Linux (LF), o que o `.gitattributes` garante.
- `scripts/empacotar_azure.py`: gera `deploy-azure.zip`, sem `.env`, `.venv`,
  testes e arquivos da AWS.
- `scripts/deploy_azure.ps1`: empacota e envia uma nova versão.
- `mercadinho/settings.py`: lê `WEBSITE_HOSTNAME` (definido pela Azure) e o
  adiciona a `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`. Usa `DB_SSLMODE` para a
  conexão SSL exigida pelo PostgreSQL da Azure.
- `estoque/management/commands/criar_admin.py`: cria o superusuário a partir de
  `DJANGO_SUPERUSER_USERNAME`/`DJANGO_SUPERUSER_PASSWORD`, somente se ele ainda
  não existir.

### Configuração inicial (feita uma única vez)

1. Crie uma conta em [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)
   com o e-mail da universidade. São US$ 100 de crédito, sem cartão.
2. Instale o Azure CLI e abra um novo terminal:

       winget install Microsoft.AzureCLI

3. Faça login e defina as variáveis no PowerShell. Use apenas letras e números
   nas senhas, pois símbolos causam problemas na linha de comando.

       az login
       $RG = "mercadinho-rg"; $LOC = "brazilsouth"
       $APP = "mercadinho-facil"; $PG = "mercadinho-pg-ygor"
       $DBPASS = "<senha-do-banco>"; $ADMINPASS = "<senha-do-admin>"
       $SECRET = python -c "import secrets; print(secrets.token_urlsafe(50))"
       az group create -n $RG -l $LOC

4. Crie o banco (leva de 5 a 10 minutos). O tamanho B1ms com 32 GB é gratuito
   por 12 meses. `--public-access 0.0.0.0` libera o acesso apenas para serviços
   da Azure.

       az postgres flexible-server create -g $RG -n $PG -l $LOC `
         --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 `
         --admin-user mercadinho --admin-password $DBPASS --public-access 0.0.0.0 --yes
       az postgres flexible-server db create --resource-group $RG --server-name $PG --name mercadinho_facil

   Nas versões recentes do Azure CLI, a forma curta `-s`/`-d` não funciona no
   `db create`, por isso o comando acima usa os nomes completos das opções.

5. Crie o plano e a aplicação, depois configure as variáveis de ambiente:

       az appservice plan create -g $RG -n mercadinho-plan -l westus3 --is-linux --sku B1
       az webapp create -g $RG -p mercadinho-plan -n $APP --runtime "PYTHON:3.12"
       az webapp config appsettings set -g $RG -n $APP --settings `
         SCM_DO_BUILD_DURING_DEPLOYMENT=true DEBUG=False USE_HTTPS=True `
         DJANGO_SECRET_KEY=$SECRET DB_HOST="$PG.postgres.database.azure.com" `
         DB_NAME=mercadinho_facil DB_USER=mercadinho DB_PASSWORD=$DBPASS DB_SSLMODE=require `
         DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=$ADMINPASS
       az webapp config set -g $RG -n $APP --startup-file "sh startup.sh"
       az webapp log config -g $RG -n $APP --docker-container-logging filesystem

6. Faça o primeiro deploy (veja a próxima seção) e entre como `admin` com a
   senha definida em `$ADMINPASS`. Troque essa senha em `/admin/` depois do
   primeiro acesso. Alterar `DJANGO_SUPERUSER_PASSWORD` depois não muda a senha,
   porque o usuário só é criado quando ainda não existe.

### Publicar uma nova versão

Na raiz do projeto:

    powershell -ExecutionPolicy Bypass -File scripts\deploy_azure.ps1 -App mercadinho-facil

A Azure instala as dependências do `requirements.txt` no servidor
(`SCM_DO_BUILD_DURING_DEPLOYMENT=true`), o que leva de 3 a 10 minutos. As
migrações rodam automaticamente na inicialização. O primeiro acesso após o
deploy pode demorar de 1 a 2 minutos.

### Comandos úteis

| Tarefa | Comando |
|---|---|
| Ver logs em tempo real | `az webapp log tail -g mercadinho-rg -n mercadinho-facil` |
| Ver o estado do app | `az webapp show -g mercadinho-rg -n mercadinho-facil --query state -o tsv` |
| Reiniciar o app | `az webapp restart -g mercadinho-rg -n mercadinho-facil` |
| Pausar o banco (volta sozinho após 7 dias) | `az postgres flexible-server stop -g mercadinho-rg -n mercadinho-pg-ygor` |
| Voltar o plano para o gratuito | `az appservice plan update -g mercadinho-rg -n mercadinho-plan --sku F1` |
| Apagar tudo | `az group delete -n mercadinho-rg --yes` |

As variáveis do PowerShell (`$RG`, `$APP` etc.) se perdem ao fechar o terminal.

### Problemas encontrados e soluções

- **`Operation cannot be completed without additional quota` (F1 VMs: 0)**: a
  assinatura de estudante não tinha cota do plano gratuito F1 em Brazil South.
  O plano foi criado em `westus3`. App e banco podem ficar em regiões
  diferentes, com um pouco mais de latência.
- **Deploy falhou com HTTP 403 / app em `QuotaExceeded`**: o plano F1 ficou
  travado nesse estado logo após a criação, mesmo sem ter usado a cota.
  Solução: `az webapp stop` + `az webapp start` e, como o problema voltava,
  migrar o plano para B1 (`az appservice plan update ... --sku B1`). O B1 custa
  cerca de US$ 13/mês, descontados do crédito de estudante.
- **Trocar o nome do site**: a Azure não permite renomear um app. Foi criado um
  novo app (`mercadinho-facil`) no mesmo plano, as configurações foram copiadas
  do app antigo (`mercadinho-ygor`), o código foi publicado e o app antigo foi
  apagado. Como os dois usam o mesmo banco, os dados foram mantidos.

        $settings = az webapp config appsettings list -g $RG -n $OLD -o json | ConvertFrom-Json |
          Where-Object { $_.name -notlike "WEBSITE_*" } | ForEach-Object { "$($_.name)=$($_.value)" }
        az webapp config appsettings set -g $RG -n $NEW --settings $settings

## Observação
Esta é uma base acadêmica para a Quinzena 5. Ainda devem ser desenvolvidos/refinados: acessibilidade completa, autorização por perfil e melhorias de segurança.


## Acessibilidade e VLibras

A interface inclui a integração do **VLibras**, recurso que auxilia na tradução de conteúdos do site para Libras. Também foram incluídos recursos básicos de acessibilidade, como foco visível para navegação por teclado, labels nos campos e atributos ARIA em elementos relevantes.

> O VLibras é um recurso de acessibilidade e não substitui as boas práticas de acessibilidade web.
