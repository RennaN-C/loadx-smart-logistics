# Deploy manual LoadX — Vercel e Render

Este diretório oferece um **acionador manual**, exclusivamente para a branch
`pentest-lab`, que já é a branch de produção dos serviços de homologação.
Não observa `main`, não envia commits, não executa merge, não publica
GitHub Release, não usa Docker Compose e não altera o banco local.

## 1. Configurar uma única vez

**Atenção:** URLs de Deploy Hook são credenciais. Não as coloque no repositório,
script, terminal compartilhado ou chat.

1. No projeto Vercel `loadx-smart-logistics-frontend`, abra
   **Settings → Git → Deploy Hooks**. Crie **um** hook, chamado
   `loadx-pentest-manual`, associado à branch **pentest-lab**.
2. No serviço Render `loadx-pentest-api`, abra
   **Settings → Deploy Hook**. Copie o link do serviço, sem parâmetro `ref`.
3. No GitHub, abra
   **Settings → Secrets and variables → Actions → New repository secret**.
   Cadastre:
   - `LOADX_VERCEL_DEPLOY_HOOK_URL`: URL gerada pela Vercel.
   - `LOADX_RENDER_DEPLOY_HOOK_URL`: URL gerada pelo Render.
4. Instale o [GitHub CLI](https://cli.github.com/), se necessário, e autentique
   com `gh auth login`.

A automação valida o **nome do serviço/projeto no hook**, o SHA atual de
`pentest-lab` e a aprovação dos checks obrigatórios neste commit.
Se uma configuração estiver ausente ou errada, a execução falha sem
contornar as proteções.

## 2. Uso no Windows (PowerShell)

Da raiz do repositório:

```powershell
.\deploy\deploy-menu.ps1
```

Comandos diretos:

```powershell
.\deploy\deploy-menu.ps1 -Acao ambos
.\deploy\deploy-menu.ps1 -Acao vercel
.\deploy\deploy-menu.ps1 -Acao render
.\deploy\deploy-menu.ps1 -Acao status
```

O script pede confirmação explícita. O parâmetro `-Confirmado` permite
execução sem o prompt em automações **iniciadas conscientemente**.

Alternativa via GitHub CLI:

```powershell
gh workflow run deploy-manual.yml --repo RennaN-C/loadx-smart-logistics --ref pentest-lab --field target=both
```

Ou use **Actions → LoadX - Deploy manual (Vercel e Render) → Run workflow**
e selecione a branch `pentest-lab`.

## 3. Comportamento e limites

- A Vercel recompila o frontend associado à branch `pentest-lab`.
- O Render recompila o backend associado à mesma branch.
- O workflow **apenas confirma que os hooks aceitaram os pedidos HTTP**.
  Para confirmar publicação, consulte os novos deploys da
  [Vercel](https://vercel.com/rennan-cardoso/loadx-smart-logistics-frontend)
  (`READY`) e do [Render](https://dashboard.render.com/web/srv-db241sss728c73b0iai0)
  (`live`), além de `/ready` e do login com conta de teste.
- Mudanças não commitadas em seu PC, mudanças apenas na `main` e arquivos
  locais não são publicados. Para publicar código novo, primeiro integre o
  commit à `pentest-lab` pelo processo já estabelecido.
- `autoDeploy` continua habilitado nos provedores: um push novo em
  `pentest-lab` já pode disparar deploy automaticamente. O menu serve para
  **redeploy manual**, sem precisar gerar commit vazio.
- Se `pentest-lab` mudar durante a execução, a validação de SHA aborta.
  O hook constrói o último commit da branch configurada (não imobiliza SHA
  entre o pedido e o build). Para mudanças simultâneas, acompanhe o SHA no
  painel dos provedores antes de afirmar qual versão está publicada.
- Para ativar futuramente acompanhamento automático da `main`, será
  necessário um workflow separado e uma nova decisão. Nada aqui faz isso.
