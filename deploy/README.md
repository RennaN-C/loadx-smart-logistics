# Deploy do LoadX — desenvolvimento, Vercel e Render

O **ambiente web de testes** deve publicar a branch `desenvolvimento` como fonte única. O menu PowerShell dispara **redeploy manual**, sem push, merge, migrations, release ou atualização da `main`. A antiga branch `pentest-lab` foi aposentada em 13/11/2026. Seu estado final está preservado em `archive/pentest-lab-pre-migracao-2026-11-13`; o ambiente ativo de testes/homologação é `desenvolvimento`.

> A branch do serviço Render e a branch de produção do projeto Vercel são **configurações hospedadas**, não são escolhidas pelo `frontend/vercel.json`. Atualizar somente este repositório **não** troca essas configurações. Mantenha a URL do backend existente até planejar uma migração de domínio separada.

## 1. Troca inicial de branch nos provedores

**Vercel — projeto `loadx-smart-logistics-frontend`:**

1. Abra [Vercel](https://vercel.com/rennan-cardoso/loadx-smart-logistics-frontend) → **Settings → Git**. Confirme repositório `RennaN-C/loadx-smart-logistics`, diretório raiz `frontend` e **Production Branch = `desenvolvimento`**.
2. Em **Settings → Git → Deploy Hooks**, crie um hook exclusivo para a branch **`desenvolvimento`**. Nome sugerido: `loadx-desenvolvimento-manual`. Use exclusivamente o hook criado para `desenvolvimento`; hooks antigos da `pentest-lab` não devem ser reutilizados.
3. Preserve a configuração do proxy da API em `frontend/vercel.json`. Não altere CORS, JWT/cookies ou variáveis de ambiente sem validar login/MFA.

**Render — serviço existente `loadx-pentest-api`:**

1. Abra [Render](https://dashboard.render.com/web/srv-db241sss728c73b0iai0) → **Settings → Build & Deploy** e confirme repositório `RennaN-C/loadx-smart-logistics`, **Branch = `desenvolvimento`**.
2. Confira comandos de build/start, raiz `backend`, health check `/ready`, plano e banco conectado **antes** de salvar. A troca de branch pode iniciar deploy se `Auto-Deploy` estiver ativo.
3. Em **Settings → Deploy Hook**, use o hook do **mesmo serviço**, sem parâmetro `ref` e sem divulgar a URL. O nome antigo do serviço pode permanecer: renomear não é necessário para mudar a branch.
4. Confira migrations Alembic/compatibilidade do banco de testes. Nunca execute `down -v` nem migrações destrutivas para trocar a origem Git.

**Ordem para não misturar versões:** confirme CI aprovada em `desenvolvimento`; configure primeiro o Render e verifique que o backend ficou `live` no SHA esperado e que `/ready` funciona; só então troque a branch de produção da Vercel, acompanhe o build `READY` e valide login/MFA e navegação. Um hook HTTP 2xx **não comprova** deploy concluído.

## 2. Habilitar o acionador manual

No GitHub do repositório, em **Settings → Secrets and variables → Actions**:

- *Repository secrets* (valores sensíveis, nunca em commit/chat): `LOADX_RENDER_DEPLOY_HOOK_URL` e `LOADX_VERCEL_DEPLOY_HOOK_URL`. O segundo deve ser o **novo** hook da `desenvolvimento`.
- *Repository variable* `LOADX_DEPLOY_SOURCE_BRANCH_CONFIRMED=desenvolvimento`. Defina **somente depois de confirmar e testar os dois projetos com essa branch**. Sem a variável, o workflow falha fechado e não chama os hooks.

O workflow valida a branch exata, confere se ela não mudou desde o disparo, exige checks **Backend, Frontend e Segurança do backend** aprovados no SHA publicado. Se existir `SonarCloud Code Analysis` para o mesmo SHA, também exige aprovação; o SonarCloud de PR nem sempre cria check no SHA final do push de `desenvolvimento`. Essa ausência é informada, não confundida com aprovação. Sem os checks obrigatórios, nenhum hook é chamado.

O arquivo `.github/workflows/deploy-manual.yml` precisa estar na branch default `main` **e** na branch `desenvolvimento` para o `workflow_dispatch` ser acessível a partir da branch de trabalho. Não use o botão com a branch `main`: a validação rejeita qualquer referência diferente de `desenvolvimento`.

## 3. Uso no Windows (PowerShell)

Instale [GitHub CLI](https://cli.github.com/), execute `gh auth login` e, na raiz do repositório:

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

O menu exige a palavra `DEPLOY` como confirmação, salvo com `-Confirmado` em execução já autorizada. O script não guarda hooks, token Render/Vercel ou configurações de banco no Windows; ele usa a sessão autenticada de `gh` para chamar o GitHub Actions.

Alternativa:

```powershell
gh workflow run deploy-manual.yml --repo RennaN-C/loadx-smart-logistics --ref desenvolvimento --field target=both
```

## 4. Publicação automática e diagnóstico

Depois que ambos os provedores estiverem configurados para `desenvolvimento`, cada push/merge pode gerar novos builds **se o auto-deploy de cada provedor estiver ativo**. Isso é independente do workflow manual acima; não significa que o pipeline de CI impede automaticamente um auto-deploy disparado pelo Git.

O menu `-Acao status` lista as solicitações ao GitHub Actions. Para confirmar execução real, confira o SHA e estado `READY` na Vercel, o SHA e estado `live` no Render, `GET /ready` e fluxos básicos de login/planejamento. Configure verificações de deploy no provedor quando quiser tornar a CI um gate obrigatório também para **auto-deploy**.

Manter a `main` separada preserva as releases estáveis; A branch histórica `pentest-lab` foi arquivada; não restaure seu conteúdo integralmente. Consulte o backup apenas para recuperar histórico ou investigar regressões.
