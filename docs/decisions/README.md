# ADRs

ADR significa Architecture Decision Record. Crie um arquivo quando uma decisão mudar arquitetura, contrato, unidade, tecnologia ou regra relevante.

Formato:

```text
# ADR-XXX: título
Status: proposta | aceita | substituída
Contexto
Decisão
Consequências
```

Registros aceitos relevantes:

- `ADR-005` a `ADR-012`: regras incrementais das OC12 a OC19.
- `ADR-013`: engine integrada e sequência de carregamento da OC20.
- `ADR-014`: persistência e ciclo de vida dos planos da OC20.
- `ADR-015`: transições de pedidos e histórico atômico da OC52.
- `ADR-016`: representação de campos decimais como número JSON da OC56.
- `ADR-017`: minimização de dados pessoais e paginação uniforme da OC59.
- `ADR-018`: liveness separado de readiness com PostgreSQL e Alembic da OC58.
- `ADR-019`: inicialização segura, migration gate e isolamento dos containers.
- `ADR-020`: sessões opacas em cookie, CSRF, throttling, Argon2id e política de
  senha da D18.
- `ADR-021`: runtime de produção com Caddy/TLS, proxy confiável, segredos
  montados e papéis PostgreSQL separados.
