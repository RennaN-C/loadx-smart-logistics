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

- `ADR-004`: fronteira pública, RBAC e bootstrap administrativo; as decisões de JWT/Bearer foram substituídas pela `ADR-020`.
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
- `ADR-022`: ciclo mínimo de viagens e entregas, integração atômica com pedidos
  e histórico, gate de carregamento e vínculo 1:1 entre usuário e motorista.
- `ADR-023`: conflito e reserva operacional de caminhões entre carregamento e viagens.
- `ADR-024`: comprovante operacional como projeção auditável da conclusão da entrega.

Proposta para revisão:

- `ADR-025`: sinais operacionais e diagnóstico seguro, sem fornecedor obrigatório (OC77).

- `ADR-029`: endereços reutilizáveis e snapshot contratado do pedido (OC99), proposta para revisão.

- `ADR-030`: manutenção e disponibilidade programada da frota (OC100), proposta para revisão.

- `ADR-031`: documentos, versões e políticas de elegibilidade dos caminhões (OC101).

- `ADR-032`: documentos, renovação e elegibilidade de motoristas (OC102).
