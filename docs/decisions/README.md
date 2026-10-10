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

- `ADR-029`: endereços reutilizáveis e snapshot contratado do pedido (OC99, PR #175).
- `ADR-030`: manutenção e disponibilidade programada da frota (OC100, PR #176).
- `ADR-031`: documentos, versões e elegibilidade dos caminhões (OC101, PR #177).
- `ADR-032`: documentos, renovação e elegibilidade de motoristas (OC102, PR #178).
- `ADR-033`: anexos operacionais com storage privado local e limites de produção (OC110, PR #179).
- `ADR-034`: importação atômica de cadastros via CSV (OC104, PR #180).
- `ADR-035`: cadastro institucional monoempresa, contrato ADMIN e auditoria protegida (OC91).
- `ADR-036`: manutenção exclusiva do mock de WhatsApp nesta etapa da OC82;
  integração real adiada por orientação do solicitante em 09/10/2026.

As ADR-029 a ADR-034 foram aceitas para o escopo implementado na v1.2.0 standalone
em 09/10/2026. Aceitação da decisão técnica não implica liberação da v1.2.0
para produção, aprovação por revisor independente ou aceite de decisões futuras.

Proposta para revisão:

- `ADR-025`: sinais operacionais e diagnóstico seguro, sem fornecedor obrigatório (OC77).
