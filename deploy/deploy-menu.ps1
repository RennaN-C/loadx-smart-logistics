# Deploy manual e intencional do snapshot remoto de desenvolvimento.
# Nao faz push, merge, sincronizacao com main nem cria releases.
[CmdletBinding()]
param(
    [ValidateSet("menu", "ambos", "vercel", "render", "status")]
    [string]$Acao = "menu",
    [switch]$Confirmado
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Repositorio = "RennaN-C/loadx-smart-logistics"
$Workflow = "deploy-manual.yml"
$Branch = "desenvolvimento"

function Exigir-GitHubCli {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI ausente. Instale com: winget install --id GitHub.cli"
    }
    & gh auth status --hostname github.com 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Faça login no GitHub CLI primeiro: gh auth login"
    }
}

function Mostrar-Status {
    Write-Host ""
    Write-Host "Ultimas execucoes do deploy manual:" -ForegroundColor Cyan
    & gh run list --repo $Repositorio --workflow $Workflow --branch $Branch --limit 5 --json databaseId,status,conclusion,url,createdAt --template '{{range .}}{{.createdAt}}  {{.status}}  {{.conclusion}}  {{.url}}{{"\n"}}{{end}}'
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel consultar as execucoes. Confira se o workflow ja foi integrado."
    }
    Write-Host ""
    Write-Host "Vercel: https://vercel.com/rennan-cardoso/loadx-smart-logistics-frontend"
    Write-Host "Render: https://dashboard.render.com/web/srv-db241sss728c73b0iai0"
    Write-Host "O status do GitHub Actions confirma o aceite dos hooks, nao a finalizacao dos builds."
}

Exigir-GitHubCli

if ($Acao -eq "menu") {
    Write-Host ""
    Write-Host "==== LoadX | Deploy manual (desenvolvimento) ====" -ForegroundColor Cyan
    Write-Host "1 - Publicar Vercel e Render"
    Write-Host "2 - Publicar apenas Vercel"
    Write-Host "3 - Publicar apenas Render"
    Write-Host "4 - Consultar ultimas solicitacoes"
    Write-Host "0 - Sair"
    $escolha = Read-Host "Selecione"
    switch ($escolha) {
        "1" { $Acao = "ambos" }
        "2" { $Acao = "vercel" }
        "3" { $Acao = "render" }
        "4" { $Acao = "status" }
        "0" { return }
        default { throw "Opcao invalida." }
    }
}

if ($Acao -eq "status") {
    Mostrar-Status
    return
}

$destino = switch ($Acao) {
    "ambos" { "both" }
    "vercel" { "vercel" }
    "render" { "render" }
}

Write-Host ""
Write-Host "O deploy usara o codigo REMOTO de '$Branch', nao arquivos locais." -ForegroundColor Yellow
Write-Host "Alvo: $Acao. Nao faz push, merge, release nem muda a branch main."
if (-not $Confirmado) {
    $resposta = Read-Host "Digite DEPLOY para confirmar"
    if ($resposta -cne "DEPLOY") {
        Write-Host "Operacao cancelada."
        return
    }
}

& gh workflow run $Workflow --repo $Repositorio --ref $Branch --field "target=$destino"
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao solicitar o deploy. Confira o GitHub CLI e se o workflow existe em desenvolvimento."
}

Write-Host ""
Write-Host "Solicitacao enviada ao GitHub Actions." -ForegroundColor Green
Write-Host "Confira a execucao e os deploys nos paineis Vercel/Render."
Mostrar-Status
