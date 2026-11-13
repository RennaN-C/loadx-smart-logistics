# Guia rápido de manutenção do LoadX

Este guia é para quem vai **abrir o repositório e alterar uma funcionalidade manualmente**. Use-o junto de [CONTRIBUTING](../CONTRIBUTING.md) e [AGENTS](../AGENTS.md); não substitui os contratos e regras de negócio.

## 1. Encontre onde alterar

| Preciso alterar | Comece por | Depois confira |
| --- | --- | --- |
| Tela, botão, formulário ou mensagem | `frontend/src/features/<recurso>/` | Componentes compartilhados em `frontend/src/components/` |
| Rotas, menus e layout | `frontend/src/app/` | Guardas e permissões de frontend |
| Chamadas HTTP do frontend | `frontend/src/features/<recurso>/api/` | Endpoint correspondente no backend |
| Regras de negócio de um módulo | `backend/app/modules/<modulo>/service.py` | Testes, `repository.py` e contrato API |
| Endpoint da API | `backend/app/modules/<modulo>/router.py` | `schemas.py`, permissões e service |
| Consulta ao banco | `backend/app/modules/<modulo>/repository.py` | Models e migrations |
| Mudança de tabela/coluna | `backend/migrations/` | Modelo de dados, testes e compatibilidade |
| Integração externa | `backend/app/integrations/` | Configuração, segurança e testes de adapter |
| Otimizador de carga | `backend/app/modules/load_planning/optimizer/` | Regras físicas e testes de regressão |
| Assistente Loxi | `backend/app/modules/assistant/` e `frontend/src/features/assistant/` | Permissões e dados reais; LLM não executa gravações |
| Documentação técnica e decisões | `docs/README.md` e `docs/decisions/` | Versão/ADR/Issue do comportamento |

Para descobrir o nome do módulo, comece pela pasta `frontend/src/features/` ou `backend/app/modules/`. Leia o `README.md` do módulo antes de editar; arquivos `*.test.ts(x)` e `test_*.py` indicam os comportamentos que precisam continuar funcionando.

## 2. Execute o sistema localmente

Na raiz do repositório, com Docker instalado:

```powershell
Copy-Item .env.example .env
# Edite .env e defina POSTGRES_PASSWORD com uma senha local.
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Abra `http://localhost:5173` para o frontend e `http://localhost:8000/docs` para a API local. Para problemas de inicialização, consulte o [guia de execução completo](13-guia-execucao-ambientes.md). **Não** use `docker compose down -v` sem querer apagar dados do banco local.

## 3. Faça uma alteração pequena e rastreável

1. Abra/identifique uma Issue e crie uma branch a partir de `desenvolvimento`; não edite `main` diretamente.
2. Localize a tela ou regra usando a tabela acima. Consulte os contratos em [docs/05](05-contratos-api.md) e as regras em [docs/04](04-regras-negocio.md).
3. Altere o menor conjunto de arquivos possível. Não duplique o mesmo estado, regra de negócio ou componente em pastas diferentes.
4. Atualize o teste do comportamento e a documentação **quando o contrato mudar**.
5. Abra PR para `desenvolvimento`, vinculada à Issue, e aguarde CI/revisão. Para mudanças em `pentest-lab`, isole os ajustes exclusivos da homologação.

## 4. Valide antes da PR

Frontend, com Node.js definido em `frontend/.nvmrc`:

```powershell
Set-Location frontend
npm ci --ignore-scripts
npm run lint
npm test -- --run
npm run build
```

Backend, com Python 3.12 e dependências do lock instalado, dentro de `backend/`:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -q tests
```

**Atenção:** integração backend exige PostgreSQL 16 de **teste isolado** e `TEST_DATABASE_URL` apontando para ele. Veja [configuração de testes](13-guia-execucao-ambientes.md#ambiente-de-testes) antes de executar. A CI é a verificação final; testes unitários não substituem a avaliação visual de telas alteradas.

## 5. O que não apagar na limpeza

- Migrations Alembic antigas: bases existentes dependem do histórico.
- Testes, contratos, scripts de build/CI, arquivos de lock, assets referenciados e exemplos de ambiente.
- Recursos que pareçam inativos, mas são carregados dinamicamente, acionados pelo backend, pelo navegador, por jobs ou por flags.
- Informações de auditoria ou dados reais sem uma política específica de retenção e autorização.

Capturas e relatórios antigos de QA **não precisam estar no checkout atual**: os índices em [evidências](evidencias/README.md) e [validações](validacoes/README.md) apontam para os commits históricos. Para novos resultados, prefira artefatos da CI e anexos de PR/Issue.

## 6. Deploy de testes com PowerShell

O projeto possui o [guia de deploy](../deploy/README.md) e o menu `deploy/deploy-menu.ps1`. O código do ambiente de testes deve ser publicado **a partir de `desenvolvimento`** após as verificações de CI; a Vercel e o Render precisam estar configurados para acompanhar essa branch nos respectivos painéis.

O menu somente solicita um redeploy no GitHub Actions. Não use o comando para substituir releases da `main`; consulte o status `READY` / `live` nos provedores antes de confirmar a publicação.

## 7. Como pensar nas branches

- `main`: referência das releases estáveis; não é local para experimentos.
- `desenvolvimento`: integração de melhorias revisadas e testadas.
- `pentest-lab`: homologação que pode ter mudanças exclusivas de interface e deploy.
- `feat/`, `fix/`, `chore/`: branches pequenas de trabalho.

**Não sincronize `pentest-lab` inteira sobre `desenvolvimento`**: promova por PR apenas os arquivos e contratos necessários, preservando o histórico e o código específico de cada ambiente. Multiempresa ainda é proposta ([ADR-049](decisions/ADR-049-multiempresa-organizacoes-isolamento.md)), não funcionalidade pronta.
