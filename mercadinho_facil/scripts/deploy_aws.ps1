<#
  Publica o projeto no AWS Elastic Beanstalk usando o AWS CLI.

  - Primeira execução: cria a aplicação e o ambiente (servidor único t3.micro).
  - Execuções seguintes: envia uma nova versão do código e atualiza o ambiente.

  Uso (na raiz do projeto):
    powershell -ExecutionPolicy Bypass -File scripts\deploy_aws.ps1
#>
param(
    [string]$App = "mercadinho-facil",
    [string]$Ambiente = "mercadinho-env",
    [string]$Regiao = "us-east-1"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Executar([scriptblock]$comando, [string]$etapa) {
    $saida = & $comando
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $etapa" }
    return $saida
}

Write-Host "1/4 Empacotando o código..."
Executar { python scripts/empacotar.py } "empacotar" | Write-Host

$versao = "v" + (Get-Date -Format "yyyyMMdd-HHmmss")

Write-Host "2/4 Enviando para o S3..."
$existe = aws elasticbeanstalk describe-applications --application-names $App --region $Regiao --query "length(Applications)" --output text
if ($LASTEXITCODE -ne 0) { throw "Falhou: verificar aplicação" }
if ($existe -eq "0") {
    Executar { aws elasticbeanstalk create-application --application-name $App --region $Regiao } "criar aplicação" | Out-Null
}
$bucket = Executar { aws elasticbeanstalk create-storage-location --region $Regiao --query S3Bucket --output text } "obter bucket"
$chave = "$App/$versao.zip"
Executar { aws s3 cp mercadinho-aws.zip "s3://$bucket/$chave" --region $Regiao } "enviar zip" | Write-Host

Write-Host "3/4 Registrando a versão $versao..."
Executar { aws elasticbeanstalk create-application-version --application-name $App --version-label $versao --source-bundle "S3Bucket=$bucket,S3Key=$chave" --region $Regiao } "criar versão" | Out-Null

$status = aws elasticbeanstalk describe-environments --application-name $App --environment-names $Ambiente --no-include-deleted --region $Regiao --query "Environments[0].Status" --output text
if ($LASTEXITCODE -ne 0) { throw "Falhou: verificar ambiente" }

if ($status -eq "None" -or [string]::IsNullOrEmpty($status)) {
    Write-Host "4/4 Criando o ambiente $Ambiente (leva ~5 min)..."
    $plataforma = Executar { aws elasticbeanstalk list-available-solution-stacks --region $Regiao --query "SolutionStacks[?contains(@, 'Amazon Linux 2023') && contains(@, 'Python 3.12')] | [0]" --output text } "obter plataforma"
    $segredo = Executar { python -c "import secrets; print(secrets.token_urlsafe(50))" } "gerar chave"
    $ns = "Namespace=aws:elasticbeanstalk:application:environment"
    Executar { aws elasticbeanstalk create-environment --application-name $App --environment-name $Ambiente `
        --solution-stack-name "$plataforma" --version-label $versao --region $Regiao --option-settings `
        "Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance" `
        "Namespace=aws:elasticbeanstalk:environment,OptionName=ServiceRole,Value=aws-elasticbeanstalk-service-role" `
        "Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=aws-elasticbeanstalk-ec2-role" `
        "Namespace=aws:ec2:instances,OptionName=InstanceTypes,Value=t3.micro" `
        "$ns,OptionName=DEBUG,Value=False" `
        "$ns,OptionName=DJANGO_SECRET_KEY,Value=$segredo" `
        "$ns,OptionName=ALLOWED_HOSTS,Value=.elasticbeanstalk.com" } "criar ambiente" | Out-Null
    Executar { aws elasticbeanstalk wait environment-exists --environment-names $Ambiente --region $Regiao } "aguardar criação"
} else {
    Write-Host "4/4 Atualizando o ambiente $Ambiente..."
    Executar { aws elasticbeanstalk update-environment --environment-name $Ambiente --version-label $versao --region $Regiao } "atualizar ambiente" | Out-Null
    Executar { aws elasticbeanstalk wait environment-updated --environment-names $Ambiente --region $Regiao } "aguardar atualização"
}

$url = aws elasticbeanstalk describe-environments --environment-names $Ambiente --region $Regiao --query "Environments[0].CNAME" --output text
Write-Host "Pronto! Versão $versao publicada em: http://$url"
