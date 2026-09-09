# Planejamento da v1.1.0

## Objetivo

`CONFIRMADO`: a v1.1.0 é a evolução pós-v1.0.0 voltada à qualidade dos cadastros,
disponibilidade e status da frota, indicadores operacionais, controle de acesso,
conferência por código, observabilidade e estrutura operacional para comprovante
de entrega. A divisão OC62–OC78 foi aprovada pela equipe na solicitação deste
planejamento.

`CONFIRMADO`: este registro oficializa escopo e responsáveis. Todas as 17 OCs
começam com status **PENDENTE**. Não representa implementação nem conclusão de
funcionalidades. A descrição detalhada e os critérios de aceite ficarão nas
Issues do GitHub; estes arquivos contêm somente resumos de planejamento.

`PENDENTE DE DEFINIÇÃO`: detalhamento das Issues, contratos, critérios de aceite,
prazos e decisões técnicas de cada ocorrência. Mudanças de dados, permissões,
contratos e regras continuam seguindo os documentos oficiais e as ADRs.

## Referências e numeração

`CONFIRMADO`: OC01–OC61 são histórico do projeto e permanecem sem renumeração.
OC01–OC48 constam na [divisão da equipe](../../07-divisao-equipe.md);
OC49–OC60 estão nas [propostas do backend](../../12-ocorrencias-propostas-backend.md)
e OC61 está registrada na
[ADR-021](../../decisions/ADR-021-runtime-producao-tls-proxy-e-segredos.md).
Esses registros conservam seus títulos, decisões e resultados históricos.

`CONFIRMADO`: **OC62 é a primeira ocorrência nova pós-v1.0.0**. A v1.1.0 usa
exclusivamente **OC62–OC78**, sem reutilizar números anteriores. A seleção desta
versão e as evoluções fora dela estão no
[roadmap](../../10-roadmap-inicial.md#roadmap-pós-v100).

## Divisão oficial

`CONFIRMADO`: números, títulos, responsáveis e áreas seguem a divisão aprovada.
`RECOMENDAÇÃO`: a coluna de dependências propõe a sequência de integração, a ser
detalhada nas Issues. “Nenhuma OC anterior” significa que não há pré-requisito
entre as novas OCs; a base v1.0.0 e seus contratos continuam sendo necessários.
Alinhamento entre devs não significa dependência circular de conclusão.

| OC / título | Responsável | Área | Dependência recomendada |
|---|---|---|---|
| OC62 — Integração ViaCEP no backend | Renan | Backend / integração | Nenhuma OC anterior da v1.1.0. |
| OC63 — Validação formal de CPF, CNPJ, CNH e telefone | Renan | Backend / cadastros | Nenhuma OC anterior da v1.1.0. |
| OC64 — Regra de conflito de caminhões | Renan | Backend / operação | Nenhuma OC anterior da v1.1.0; alinhar conceitos com OC65. |
| OC65 — Regra de conflito de motoristas | Renan | Backend / operação | Nenhuma OC anterior da v1.1.0; alinhar conceitos com OC64. |
| OC66 — RBAC granular de carregamento e conferência | Renan | Backend / autorização | Nenhuma OC anterior da v1.1.0; alinhar permissões com Marcelo e Marlon para OC76 e OC75. |
| OC67 — Serviço de disponibilidade da frota | João | Backend / frota | OC64 e OC65 (Renan). |
| OC68 — API de status operacional dos caminhões | João | Backend / API | OC67 (João). |
| OC69 — API de indicadores operacionais | João | Backend / API | OC67 e OC68 (João). |
| OC70 — ViaCEP no cadastro de clientes | Marlon | Frontend / clientes | OC62 (Renan). |
| OC71 — Validações e feedback dos documentos | Marlon | Frontend / cadastros | OC63 (Renan). |
| OC72 — Interface de disponibilidade de caminhões e motoristas | Marlon | Frontend / disponibilidade | OC64 e OC65 (Renan) e OC67 (João); alinhar o contrato de consulta de motoristas entre os três. |
| OC73 — Painel de status da frota | Marlon | Frontend / frota | OC68 (João). |
| OC74 — Dashboard operacional | Marlon | Frontend / indicadores | OC69 (João). |
| OC75 — Conferência por QR Code/código de barras | Marlon | Frontend / conferência | OC66 (Renan) e OC76 (Marcelo). |
| OC76 — Backend da conferência por QR Code/código de barras | Marcelo | Backend / conferência | OC66 (Renan); alinhar contrato com Marlon para OC75. |
| OC77 — Observabilidade de produção | Marcelo | Operação / observabilidade | Nenhuma OC anterior da v1.1.0; alinhamento transversal com os quatro desenvolvedores. |
| OC78 — Estrutura operacional para comprovante de entrega | Marcelo | Backend / entregas | Nenhuma OC anterior da v1.1.0; alinhar com Renan o ciclo de entregas existente. |

## Ordem recomendada de execução

`RECOMENDAÇÃO`:

1. Detalhar as Issues e combinar contratos, regras de conflito, permissões e
   critérios de aceite entre os responsáveis.
2. Renan executar OC62, OC63, OC64, OC65 e OC66. Marcelo pode iniciar OC77 e o
   planejamento da OC78 em paralelo, após as definições próprias de cada Issue.
3. João executar OC67 após OC64/OC65, depois OC68 e OC69. Marlon pode integrar
   OC70 após OC62 e OC71 após OC63; Marcelo pode executar OC76 após OC66.
4. Marlon integrar OC72 após OC64/OC65/OC67, OC73 após OC68, OC74 após OC69 e
   OC75 após OC66/OC76. Marcelo concluir OC77 e OC78 conforme seus critérios de
   aceite e o alinhamento com os módulos envolvidos.
5. Os quatro desenvolvedores validar os fluxos integrados, testes e documentação
   em `desenvolvimento`, preparar `release/v1.1.0` e revisar a entrega para `main`.

`RECOMENDAÇÃO`: a ordem é por dependência, sem exigir que um desenvolvedor
termine todo o seu lote para liberar o próximo. Telas podem ser preparadas com
mocks de contratos acordados; o aceite integrado depende dos serviços reais.

## Dependências entre desenvolvedores

`RECOMENDAÇÃO`:

- **Renan → João:** OC64/OC65 fornecem as regras para OC67 e, por consequência,
  para OC68/OC69.
- **Renan → Marlon:** OC62 sustenta OC70; OC63 sustenta OC71; OC64/OC65 sustentam
  OC72 junto de OC67; OC66 orienta as permissões de OC75.
- **João → Marlon:** OC67 sustenta OC72, OC68 sustenta OC73 e OC69 sustenta OC74.
- **Renan → Marcelo → Marlon:** OC66 orienta OC76; o contrato de OC76 viabiliza
  OC75. Os três devem combinar autorização e conferência antes da integração.
- **Marcelo ↔ equipe:** OC77 acompanha os fluxos entregues pelos quatro; OC78
  exige alinhamento com Renan sobre o ciclo de entregas existente.

`PENDENTE DE DEFINIÇÃO`: Renan, João e Marlon devem explicitar nas Issues de
OC65/OC67/OC72 como a disponibilidade de motoristas será consultada pela
interface. Este planejamento não cria um endpoint ou um estado operacional.
A matriz granular de acesso, o formato dos códigos, os indicadores, os meios de
observabilidade e os limites do comprovante também serão detalhados nas Issues.

## Fluxo Git

`CONFIRMADO`: o fluxo da v1.1.0 é:

```text
branch do dev -> desenvolvimento -> release/v1.1.0 -> main
```

`RECOMENDAÇÃO`: usar uma branch por ocorrência a partir de `desenvolvimento`,
com nomes no formato `<desenvolvedor>/ocNN-descricao`, em minúsculas e sem
acentos, como `renan/oc62-viacep-backend`. Os nomes sugeridos estão nos arquivos
individuais. PRs de trabalho seguem para
`desenvolvimento`; a versão integrada passa por `release/v1.1.0` antes da
promoção para `main`, com revisão de outro integrante e validações do projeto.

`CONFIRMADO`: estes documentos serão versionados normalmente nesse fluxo.
Não criar diferenças artificiais entre `main` e `desenvolvimento` para ocultar
documentação. Este trabalho não cria branches, commits, push ou merge.

## Planejamento por desenvolvedor

- [DEV 1 — Renan: OC62–OC66](01-renan.md).
- [DEV 2 — João: OC67–OC69](02-joao.md).
- [DEV 3 — Marlon: OC70–OC75](03-marlon.md).
- [DEV 4 — Marcelo: OC76–OC78](04-marcelo.md).
