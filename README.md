# LoadX Smart Logistics

**Planejamento, otimização tridimensional e acompanhamento de cargas logísticas.**

Projeto acadêmico de Engenharia de Software que integra pedidos, frota, planejamento de cargas, conferência, viagens, entregas, administração e auditoria em uma aplicação web.

**Última versão oficial: [v1.2.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0)** — publicada em **26/10/2026**. A tag preserva o código da versão lançada; a branch `main` pode receber correções e melhorias documentais posteriores.

## Funcionalidades

| Área | Recursos |
| --- | --- |
| **Planejamento de carga** | Otimização 3D, seleção de pedidos e veículos, distribuição multi-caminhão, revisão e aprovação da proposta |
| **Operação logística** | Conferência de volumes, carregamentos, viagens, entregas, ocorrências e rastreabilidade |
| **Frota e cadastros** | Clientes e endereços, produtos, pedidos, caminhões, manutenções, documentação e motoristas |
| **Administração** | Usuários, perfis e permissões, segurança da conta, MFA, sessões, empresa e auditoria |
| **Acompanhamento** | Visão Geral, notificações internas, agenda operacional, busca global e relatórios em PDF |
| **Integrações** | Contratos para webhooks, eventos duráveis/outbox e monitoramento da saúde das integrações |

**Limites conhecidos:** uma otimização síncrona aceita **até 200 volumes físicos totais**, inclusive quando distribuídos entre vários caminhões, e até **10 veículos candidatos**. O algoritmo não força a utilização de mais de um caminhão se um único veículo elegível comportar toda a carga. WhatsApp Business real ainda não está ativo (canal simulado); explicações por IA podem usar provider fake/fallback. Anexos possuem armazenamento privado local; produção exige configuração própria de persistência e backup. O LoadX v1.2.0 é **monoempresa/standalone**, sem integração CoreFlow.

## Executar localmente

**Pré-requisitos:** Git e Docker com Docker Compose. Para execução fora dos contêineres, veja o [guia de ambientes](docs/13-guia-execucao-ambientes.md).

```bash
git clone https://github.com/RennaN-C/loadx-smart-logistics.git
cd loadx-smart-logistics
```

Para reproduzir exatamente a versão publicada, execute `git checkout v1.2.0` após o clone. Não desenvolva diretamente sobre a tag.

Crie o arquivo `.env` a partir do `.env.example` e defina ao menos `POSTGRES_PASSWORD` com senha local própria.

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

No Linux/macOS, use `cp .env.example .env` em vez de `Copy-Item`.

| Serviço | URL local |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger (APP_ENV=local) | http://localhost:8000/docs |
| Saúde e prontidão | http://localhost:8000/health e http://localhost:8000/ready |

O Compose aguarda o serviço `migrate` aplicar as migrations antes de iniciar a API. O head Alembic da v1.2.0 é `20261023_0035`. Para criar o primeiro administrador, consulte [backend/README.md](backend/README.md).

**Preservação de dados:** `docker compose down` encerra os serviços; `docker compose down -v` **remove volumes locais e não deve ser usado para atualização**. Não use `alembic stamp` para encobrir migrations ausentes.

## Tecnologias e arquitetura

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, Alembic e Pytest.
- **Frontend:** React, TypeScript, Vite, Three.js, React Three Fiber e Vitest.
- **Banco:** PostgreSQL 16.
- **Ferramentas:** Docker Compose, GitHub Actions, Ruff, ESLint e SonarCloud.

Arquitetura de **monólito modular**, com separação entre API, regras de domínio, banco e integrações. A otimização física é determinística: IA generativa não aprova posicionamento de volumes.

## Documentação

- [Índice da documentação](docs/README.md) e [guia de ambientes](docs/13-guia-execucao-ambientes.md)
- [Arquitetura](docs/02-arquitetura.md), [regras de negócio](docs/04-regras-negocio.md) e [contratos API](docs/05-contratos-api.md)
- [Roadmap de versões](docs/planejamento/roadmap-versoes.md), [Changelog](CHANGELOG.md) e [notas técnicas da v1.2.0](docs/releases/v1.2.0.md)
- [Contribuição](CONTRIBUTING.md), [segurança](SECURITY.md) e [instruções para agentes](AGENTS.md)

## Branches e versões

| Referência | Finalidade |
| --- | --- |
| [`v1.2.0`](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0) | Snapshot da versão publicada |
| `main` | Código oficialmente consolidado e manutenção |
| `desenvolvimento` | Integração de mudanças para o próximo ciclo |
| Branches de ocorrência | Implementação isolada com Issue, testes e revisão |
| `versao/vX.Y.Z` | Preparação de release, quando aplicável |

Fluxo: **Issue → branch → PR para `desenvolvimento` → preparação de versão → PR para `main` → tag e GitHub Release**. Tags anteriores não devem ser reescritas.

## Qualidade e limitações em acompanhamento

A preparação da v1.2.0 registrou **3.001 testes de backend**, **1.130 testes de frontend** e **95% de cobertura local do backend**, além de migrations e backup/restauração ensaiados em PostgreSQL isolado. Os checks do candidato de release foram aprovados, mas isso não significa homologação de produção.

A [Issue #268](https://github.com/RennaN-C/loadx-smart-logistics/issues/268) permanece aberta: a importação de cobertura no SonarCloud não foi comprovada apesar do Quality Gate verde. A [Issue #256](https://github.com/RennaN-C/loadx-smart-logistics/issues/256) acompanha a auditoria incremental. A aprovação do Quality Gate não encerra automaticamente os apontamentos da análise.

**Histórico:** [v1.0.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.0.0) · [v1.1.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.1.0) · [v1.2.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0).
