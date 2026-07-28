# Estrutura de pastas

```text
├── .github
│   ├── ISSUE_TEMPLATE
│   │   ├── feature.yml
│   │   └── README.md
│   ├── copilot-instructions.md
│   ├── pull_request_template.md
│   └── README.md
├── backend
│   ├── app
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── router.py
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── README.md
│   │   ├── database
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── README.md
│   │   │   └── session.py
│   │   ├── integrations
│   │   │   ├── ai
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── whatsapp
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── modules
│   │   │   ├── auth
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── customers
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── deliveries
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── drivers
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── load_planning
│   │   │   │   ├── optimizer
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── README.md
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── loading
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── occurrences
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── orders
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── products
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── reports
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── trucks
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── users
│   │   │   │   ├── __init__.py
│   │   │   │   └── README.md
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── shared
│   │   │   ├── __init__.py
│   │   │   └── README.md
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── README.md
│   ├── migrations
│   │   └── README.md
│   ├── tests
│   │   ├── e2e
│   │   │   └── README.md
│   │   ├── integration
│   │   │   └── README.md
│   │   ├── unit
│   │   │   └── README.md
│   │   ├── README.md
│   │   └── test_health.py
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── README.md
│   └── requirements.txt
├── docs
│   ├── decisions
│   │   ├── ADR-001-monolito-modular.md
│   │   ├── ADR-002-unidades-e-coordenadas.md
│   │   ├── ADR-003-ia-como-apoio.md
│   │   └── README.md
│   ├── diagrams
│   │   └── README.md
│   ├── prompts
│   │   ├── corrigir-bug.md
│   │   ├── implementar-ocorrencia.md
│   │   ├── README.md
│   │   └── revisar-codigo.md
│   ├── 00-visao-produto.md
│   ├── 01-escopo-mvp.md
│   ├── 02-arquitetura.md
│   ├── 03-modelo-dados.md
│   ├── 04-regras-negocio.md
│   ├── 05-contratos-api.md
│   ├── 06-fluxo-operacional.md
│   ├── 07-divisao-equipe.md
│   ├── 08-padroes-desenvolvimento.md
│   ├── 09-guia-para-ia.md
│   ├── 10-roadmap-inicial.md
│   ├── README.md
│   └── referencia-arquivo-original.md
├── frontend
│   ├── src
│   │   ├── app
│   │   │   ├── App.tsx
│   │   │   ├── README.md
│   │   │   └── styles.css
│   │   ├── components
│   │   │   └── README.md
│   │   ├── features
│   │   │   ├── auth
│   │   │   │   └── README.md
│   │   │   ├── customers
│   │   │   │   └── README.md
│   │   │   ├── dashboard
│   │   │   │   └── README.md
│   │   │   ├── deliveries
│   │   │   │   └── README.md
│   │   │   ├── drivers
│   │   │   │   └── README.md
│   │   │   ├── load-planning
│   │   │   │   └── README.md
│   │   │   ├── load-visualization
│   │   │   │   └── README.md
│   │   │   ├── loading-operation
│   │   │   │   └── README.md
│   │   │   ├── occurrences
│   │   │   │   └── README.md
│   │   │   ├── orders
│   │   │   │   └── README.md
│   │   │   ├── products
│   │   │   │   └── README.md
│   │   │   ├── reports
│   │   │   │   └── README.md
│   │   │   ├── trucks
│   │   │   │   └── README.md
│   │   │   └── README.md
│   │   ├── services
│   │   │   ├── api.ts
│   │   │   └── README.md
│   │   ├── tests
│   │   │   └── README.md
│   │   ├── types
│   │   │   └── README.md
│   │   ├── main.tsx
│   │   └── README.md
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── README.md
│   ├── tsconfig.json
│   └── vite.config.ts
├── infra
│   ├── ci
│   │   └── README.md
│   ├── database
│   │   ├── seeds
│   │   │   └── README.md
│   │   └── README.md
│   ├── scripts
│   │   └── README.md
│   └── README.md
├── .env.example
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── compose.yaml
└── README.md
```
