<#
  Publica uma nova versão do projeto no Azure App Service.
  (A criação inicial dos recursos é feita uma única vez — ver README/guia.)

  Uso (na raiz do projeto):
    powershell -ExecutionPolicy Bypass -File scripts\deploy_azure.ps1 -App mercadinho-seunome
#>
param(
    [Parameter(Mandatory = $true)][string]$App,
    [string]$Grupo = "mercadinho-rg"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "1/2 Empacotando o código..."
python scripts/empacotar_azure.py
if ($LASTEXITCODE -ne 0) { throw "Falhou: empacotar" }

Write-Host "2/2 Enviando para o Azure (a instalação dos pacotes leva alguns minutos)..."
az webapp deploy -g $Grupo -n $App --src-path deploy-azure.zip --type zip
if ($LASTEXITCODE -ne 0) { throw "Falhou: deploy (veja: az webapp log tail -g $Grupo -n $App)" }

$url = az webapp show -g $Grupo -n $App --query defaultHostName -o tsv
Write-Host "Pronto! Site publicado em: https://$url"
