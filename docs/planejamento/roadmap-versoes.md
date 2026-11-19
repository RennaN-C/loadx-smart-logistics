# Roadmap de versões — LoadX Smart Logistics

## Status e governança deste documento

`CONFIRMADO`: esta é a referência canônica para o **histórico das versões publicadas** e o planejamento futuro. As releases v1.0.0, v1.1.0 e **v1.2.0** já foram publicadas. A **v1.3.0** é a versão funcional desta árvore ([PR #388](https://github.com/RennaN-C/loadx-smart-logistics/pull/388)); conferir publicação nas [Releases](https://github.com/RennaN-C/loadx-smart-logistics/releases). A v1.4.0 continua direção de produto e exige planejamento/Issues próprios antes de implementação.

`CONFIRMADO`: o histórico de construção do MVP e da seleção da v1.1.0 permanece
em `docs/10-roadmap-inicial.md`. O detalhamento oficial da v1.1.0 permanece em
`docs/planejamento/v1.1.0/`.

`RECOMENDAÇÃO`: os temas das versões futuras registram direção de produto,
responsável principal e ordem de evolução. Eles não aprovam automaticamente
novos contratos, estados, tabelas, integrações ou dependências.

`PENDENTE DE DEFINIÇÃO`: cada versão futura deverá receber planejamento próprio
antes do início da implementação.

`CONFIRMADO`: uma funcionalidade futura somente se torna trabalho autorizado
quando possuir Issue aprovada, responsável, critérios de aceite, testes mínimos
e decisões necessárias resolvidas.

---

## Política de versionamento — Semantic Versioning

O LoadX adota o formato:

`MAJOR.MINOR.PATCH`

Exemplo:

`1.2.3`

Onde:

- `MAJOR`: mudança incompatível com contratos ou comportamento anteriormente
  publicado;
- `MINOR`: novas funcionalidades compatíveis com a versão anterior;
- `PATCH`: correções de bugs em uma versão já publicada, sem nova funcionalidade
  incompatível.

### Exemplos

- `1.1.0 -> 1.1.1`: correção de bug após o lançamento da v1.1.0;
- `1.1.1 -> 1.1.2`: nova correção compatível;
- `1.1.x -> 1.2.0`: nova versão funcional;
- `1.x.x -> 2.0.0`: mudança incompatível que exige incremento de MAJOR.

`CONFIRMADO`: correções encontradas enquanto uma versão ainda está em
desenvolvimento fazem parte daquela própria versão e não geram PATCH a cada
ajuste.

`CONFIRMADO`: versões PATCH normalmente não são pré-planejadas neste roadmap. Elas surgem quando uma versão publicada exige correção compatível.

`DECISÃO SEMVER (30/10/2026)`: o Loxi, a integração Groq, as novas consultas e a experiência 3D são funcionalidades compatíveis. Por isso a release é **v1.3.0 (MINOR)**, não PATCH. A proposta multiempresa foi direcionada à **v1.4.0**; em 14/11/2026 o planejamento foi consolidado como plataforma SaaS independente.

`DECISÃO NECESSÁRIA`: o marco atualmente chamado de v2.0.0 somente deverá usar
esse número se introduzir mudança incompatível que justifique incremento de
MAJOR. Se a plataforma móvel puder ser adicionada de forma compatível, o número
correto continuará a sequência MINOR, por exemplo v1.9.0.

Este documento não altera sozinho o fluxo Git de hotfix. O processo de uma
eventual versão PATCH deverá ser definido quando a necessidade surgir.

---

## Política de numeração das OCs

`CONFIRMADO`: `OCXX` é o identificador funcional da ocorrência no LoadX.
O número da Issue do GitHub é independente e atribuído automaticamente pelo GitHub.
Uma coincidência entre os dois números não significa que a Issue e a OC sejam equivalentes.

`CONFIRMADO`: OC01–OC78 fazem parte do histórico e da v1.1.0 e seus números não
podem ser reutilizados.

`CONFIRMADO`: a v1.2.0 usa a faixa **OC79–OC112**, formalizada nas Issues
#122–#133, #136–#141 e #144–#159. O escopo reúne comunicação interna durável (WhatsApp externo ainda simulado), administração,
operação multi-caminhão, gestão operacional, segurança, frota, cadastros,
auditoria, confiabilidade de integrações e experiência de uso.

Esses números somente representam trabalho executável enquanto as respectivas
Issues permanecerem aprovadas, atribuídas e vinculadas ao planejamento da versão.

`CONFIRMADO`: números posteriores à OC112 não ficam reservados antecipadamente.
A numeração da v1.4.0 em diante será definida no momento do planejamento de cada
release, usando a próxima OC realmente disponível.

Essa regra evita engessar dezenas de números para funcionalidades que ainda
podem mudar de ordem, escopo ou versão.

---

## Distribuição principal da equipe

| Responsável | Foco principal |
|---|---|
| **Rennan — DEV 1** | Backend, banco, regras de negócio, contratos, segurança e consistência transacional |
| **João — DEV 2** | Algoritmos, cálculos, otimização, inteligência e modelos preditivos |
| **Marlon — DEV 3** | Frontend, dashboards, visualização e experiência operacional |
| **Marcelo — DEV 4** | Integrações externas, WhatsApp, notificações, mídia, observabilidade, relatórios e testes |

`CONFIRMADO`: a responsabilidade principal não impede colaboração entre os
desenvolvedores.

Mudanças de contrato público devem envolver os consumidores impactados.

Mudanças estruturais de banco envolvem o responsável de backend/dados.

Integrações externas concretas permanecem atrás de ports/adapters.

---

# v1.0.0 — Fundação operacional

`CONFIRMADO`: versão-base do produto, publicada em 09/09/2026.

Principais capacidades:

- autenticação e perfis;
- cadastros;
- pedidos;
- planejamento tridimensional;
- algoritmo determinístico de posicionamento;
- visualização 3D;
- carregamento e conferência;
- viagens e entregas;
- ocorrências;
- relatórios;
- WhatsApp simulado/controlado;
- IA com provider fake e fallback;
- infraestrutura e CI/CD.

As entregas oficiais permanecem registradas no `CHANGELOG.md`.

---

# v1.1.0 — Maturidade operacional

`CONFIRMADO`: versão publicada em 2026-10-06.

Objetivo:

fortalecer qualidade de dados, disponibilidade operacional, autorização,
conferência, indicadores e capacidade de operação em produção.

Escopo planejado:

- ViaCEP;
- validações formais;
- conflitos de caminhões;
- conflitos de motoristas;
- disponibilidade da frota;
- status operacional da frota;
- indicadores;
- dashboard operacional;
- RBAC granular de carregamento;
- QR Code / código de barras;
- observabilidade;
- estrutura operacional para comprovante de entrega.

Planejamento detalhado:

`docs/planejamento/v1.1.0/`

---

# v1.2.0 — Consolidação do produto e operação avançada (publicada)

**Estado:** publicada em **26/10/2026**: [release oficial](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0), PR #314. O planejamento abaixo é histórico; a implementação efetivamente lançada e as limitações estão no [Changelog](../../CHANGELOG.md) e nas [notas técnicas](../releases/v1.2.0.md). WhatsApp Business real não integra esta entrega e a cobertura SonarCloud segue na Issue #268.

## Objetivo

`CONFIRMADO`: a v1.2.0 concentra a maior etapa de consolidação funcional do LoadX
antes da futura camada de multi-tenancy logístico e administração SaaS própria. O objetivo
é fechar lacunas de administração, segurança, operação, frota, cadastros, auditoria,
integrações e experiência de uso, sem retirar a autoridade das regras de domínio do backend.

`CONFIRMADO`: a v1.2.0 continua **monoempresa e standalone**. Ela não implementa tenancy, licenciamento, billing ou tenant_id no domínio.

`REGISTRO HISTÓRICO, SUBSTITUÍDO EM 14/11/2026`: as OCs administrativas da v1.2.0 eram limitadas ao escopo operacional. A v1.4.0 passa a dar ao próprio LoadX a responsabilidade de identidade global, organização, licenciamento e administração de plataforma. As Issues #128, #129, #136, #137, #145 e #159 permanecem referências históricas.

### Hierarquia de perfis do LoadX na v1.2.0

`CONFIRMADO` (08/10/2026): `ADMIN` é superconjunto de funções gerenciais e de
conferência **internas ao LoadX**; `LOGISTICS_MANAGER` fica restrito à gestão
operacional e não pode administrar usuários, credenciais de terceiros,
configuração institucional, segurança de conta ou perfis/permissões. `CHECKER`
opera conferência e `DRIVER` operações próprias validadas por vínculo.

O planejamento previu ajustar a matriz de permissões antes da expansão das telas OC85/OC86. A OC112 compreendeu perfis personalizados e permissões logísticas, mantendo a autorização no backend. Nem `ADMIN` nem perfil customizado obtém automaticamente direito
de plataforma, gestão comercial, tenant ou entitlement de módulos; todas as regras de domínio,
auditoria e autoria das ações continuam obrigatórias.

## Planejamento histórico do ciclo v1.2.0

A tabela mantém os responsáveis inicialmente previstos, com mudanças posteriores de atribuição durante a execução. Para autoria efetiva, consultar as Issues/PRs integradas.

| OC | Issue | Responsável | Entrega planejada |
|---|---:|---|---|
| OC79 | #122 | Rennan | Segurança, autorização e idempotência de comandos externos |
| OC80 | #123 | Rennan | Contrato de evidências e comprovante de entrega |
| OC81 | #124 | Marlon | Interface de comprovante e comunicação operacional |
| OC82 | #125 | Marcelo | Adapter mock de WhatsApp; integração real adiada para #193 |
| OC83 | #126 | Marcelo | Webhook, recebimento de mensagens e mídia |
| OC84 | #127 | Marcelo | Notificações internas reais; canal WhatsApp mock |
| OC85 | #128 | Marlon | Área de configurações administrativas |
| OC86 | #129 | Marlon | Gestão de usuários pelo administrador |
| OC87 | #130 | Rennan | Modelo e regras para planejamento multi-caminhão |
| OC88 | #131 | João | Otimização automática com múltiplos caminhões |
| OC89 | #132 | Marlon | Planejamento multi-caminhão no frontend |
| OC90 | #133 | Marcelo | Fluxo operacional e auditoria do multi-caminhão |
| OC91 | #136 | Rennan | Configurações gerais da empresa atual |
| OC92 | #137 | Rennan | Meu perfil, alteração de senha e sessões |
| OC93 | #138 | Marlon | Central de carregamentos, viagens e entregas |
| OC94 | #139 | Marcelo | Exceções operacionais, reentrega e cancelamento |
| OC95 | #140 | João | Busca e filtros avançados no servidor |
| OC96 | #141 | Marcelo | Relatórios gerenciais e exportações |
| OC97 | #144 | Rennan | Histórico e auditoria do sistema |
| OC98 | #145 | Rennan | Recuperação de senha e autenticação multifator |
| OC99 | #146 | Rennan | Múltiplos endereços por cliente |
| OC100 | #147 | Rennan | Manutenção e disponibilidade programada da frota |
| OC101 | #148 | Rennan | Documentos e vencimentos dos caminhões |
| OC102 | #149 | Rennan | Documentos e vencimentos dos motoristas |
| OC103 | #150 | Rennan | Central de notificações no sistema |
| OC104 | #151 | Rennan | Importação em massa de cadastros |
| OC105 | #152 | Rennan | Arquivamento e reativação de cadastros |
| OC106 | #153 | Rennan | Agenda operacional de carregamentos, viagens e entregas |
| OC107 | #154 | Rennan | Busca global do sistema |
| OC108 | #155 | Rennan | Painel de integrações e saúde operacional |
| OC109 | #156 | Rennan | Fila de eventos, retentativas e reprocessamento |
| OC110 | #157 | Rennan | Anexos e documentos operacionais |
| OC111 | #158 | Rennan | Linha do tempo unificada da operação |
| OC112 | #159 | Rennan | Perfis e permissões administrativas flexíveis |

Planejamento detalhado:

`docs/planejamento/v1.2.0/00-visao-geral.md`

WhatsApp real foi adiado para a pré-produção (#193). A OC83 pode entregar webhook interno funcional e autenticado; a OC84 produzirá notificações reais do domínio, mantendo o envio externo simulado. A IA poderá usar integração real aprovada com credenciais protegidas. Ver ADR-037.

## Dependências principais

`CONFIRMADO`:

- OC79 fornece a base de segurança e idempotência para OC82, OC83 e OC84;
- OC80 define o contrato de evidências consumido por OC81, OC83 e OC110;
- OC85 fornece a área de navegação para OC86, OC91 e OC92;
- OC87 define o modelo e as regras transacionais que bloqueiam OC88, OC89 e OC90;
- OC94 depende de OC87 e OC84; OC93 e OC96 dependem da consolidação de OC90/OC94;
- OC98 depende da base de conta e sessões da OC92;
- OC103 depende das notificações operacionais reais da OC84;
- OC106 depende da central operacional da OC93;
- OC107 reutiliza a busca server-side definida na OC95;
- OC108 depende da base de integração da OC82 e incorpora os demais estados quando disponíveis;
- OC109 depende da notificação real da OC84 e permanece compatível com OC82/OC83;
- OC111 agrega auditoria e central operacional, dependendo de OC97 e OC93; as exceções chegam por OC93/OC94;
- OC112 depende da gestão de usuários da OC86;
- OC97, OC99, OC100, OC101, OC102, OC104 e OC105 podem evoluir sem bloqueador funcional novo.

## Resultado esperado

O planejamento da v1.2.0 estabeleceu os seguintes objetivos; seu aceite de código e as limitações constam da release:

- possuir administração interna, configurações, gestão de usuários, perfil e segurança de conta;
- suportar notificações internas, evidências, anexos e integrações resilientes, mantendo o envio externo por WhatsApp simulado;
- operar carga em um ou vários caminhões preservando rastreabilidade;
- oferecer central operacional, agenda, exceções, reentrega e cancelamento;
- possuir manutenção, documentos e vencimentos de frota e motoristas;
- permitir múltiplos endereços por cliente e importação/arquivamento de cadastros;
- oferecer busca por módulo e busca global no servidor;
- apresentar auditoria, linha do tempo, notificações internas e relatórios gerenciais;
- expor saúde das integrações ao ADMIN sem revelar segredos;
- permitir perfis administrativos flexíveis sem retirar a autorização do backend.

---
# v1.3.0 — Loxi e Experiência Inteligente

**Escopo da versão:** a [PR #388](https://github.com/RennaN-C/loadx-smart-logistics/pull/388) consolida a evolução. A publicação oficial depende de aprovação da CI, integração na `main` e criação da [tag/release](https://github.com/RennaN-C/loadx-smart-logistics/releases), sem certificar deploy externo. As [notas da candidata](../releases/v1.3.0.md) e o [Changelog](../../CHANGELOG.md) detalham o escopo.

## Entregas da versão

- **Loxi (Groq):** conversa natural, perguntas de acompanhamento e contexto limitado; fallback quando o provider não responde. Não depende de WhatsApp real.
- **Consultas verificadas:** frota, disponibilidade e motivos autorizados, indicadores e planejamentos persistidos, com dados e permissões revalidados pelo backend. Fontes operacionais não são inventadas pela IA.
- **Explicação de planejamento:** situação, volumes carregados/rejeitados, peso, ocupação geométrica e capacidade restante do snapshot; não garante solução ótima global nem executa novo cálculo automaticamente.
- **Experiência visual:** cartões operacionais, painel conversacional expansível, interface responsiva e prévia 3D compacta sob demanda, preservando o visualizador já existente.
- **Segurança:** acesso por perfis/permissões, limites e falhas explícitas do provider, proteção contra injeção de instruções e leitura autorizada. O chat **não executa comandos de escrita**; ações de alteração continuam nas telas e services apropriados.

**Limites mantidos:** LoadX monoempresa/standalone, limite atual de **200 volumes físicos totais** por otimização síncrona e até **10 veículos candidatos**; não inclui multiempresa, tenant_id, cobrança SaaS, WhatsApp Business real, storage externo de produção nem automações de escrita pelo Loxi. A disponibilização da chave e o teste Groq ao vivo dependem de configuração do ambiente.

**Gate de publicação:** checks Backend, Frontend, Segurança e SonarCloud na PR. Após merge, o job de publicação exige a CI interna da `main` aprovada **e valida explicitamente o check SonarCloud do SHA exato do push** antes de criar tag/release; falha, ausência e timeout bloqueiam publicação. Isso não representa deploy no Render/Vercel.

## Manutenção ativa e critérios de fechamento

- [#382](https://github.com/RennaN-C/loadx-smart-logistics/issues/382): estabilização do Loxi, contexto, Groq, verificações e testes; a presença da funcionalidade na versão **não encerra automaticamente** a Issue.
- [#368](https://github.com/RennaN-C/loadx-smart-logistics/issues/368): ações operacionais confirmáveis, RBAC e auditoria — **futuro**; exige proposta, revalidação server-side, prévia, confirmação, idempotência e trilha de auditoria.
- [#254](https://github.com/RennaN-C/loadx-smart-logistics/issues/254): desempenho e resposta ao usuário da otimização multi-caminhão; revalidar tempos e recuperação antes de declarar resolvido.
- [#268](https://github.com/RennaN-C/loadx-smart-logistics/issues/268) e [#256](https://github.com/RennaN-C/loadx-smart-logistics/issues/256): cobertura SonarCloud e auditoria incremental. A [triagem da PR #388](../qualidade/sonarcloud-pr388-20261030.md) registra 118 apontamentos, ainda sem classificação individual por severidade.
- [#248](https://github.com/RennaN-C/loadx-smart-logistics/issues/248) e [#242](https://github.com/RennaN-C/loadx-smart-logistics/issues/242): entrega/diagnóstico de e-mail e recuperação de senha exigem validação do ambiente, não apenas testes locais.
- [#323](https://github.com/RennaN-C/loadx-smart-logistics/issues/323): decisão entre exclusão e arquivamento seguro de cadastros.
- [#193](https://github.com/RennaN-C/loadx-smart-logistics/issues/193): ativar WhatsApp Business real somente quando provider, autenticação e operação forem aprovados.
- [#364](https://github.com/RennaN-C/loadx-smart-logistics/issues/364), [#370](https://github.com/RennaN-C/loadx-smart-logistics/issues/370) e [#377](https://github.com/RennaN-C/loadx-smart-logistics/issues/377): revisar/sincronizar branches, distinguindo backports pendentes de código já integrado.

As Issues acima são um retrato das pendências abertas em 30/10/2026; consultar o GitHub para seu estado mais recente. Nem toda pendência exige outra versão, mas nenhuma deve ser considerada concluída apenas por constar no roadmap.

---

# Backlog transversal pós-v1.3.0 — versão a definir

Estes são **objetivos e propostas**, não recursos disponíveis, OCs reservadas ou compromissos de inclusão automática na v1.4.0:

1. **Escala do otimizador:** investigar evolução do limite de 200 para **1.000 ou mais volumes** por operação, incluindo consumo de CPU/memória, duração, filas, idempotência, timeouts, benchmarks com PostgreSQL, recuperação e UX para processamentos demorados. A meta depende de critérios de desempenho e testes de segurança/física.
2. **Embalagens/unidades logísticas:** estudar tipos como caixas, paletes e outros agrupadores, dimensões externas, tara, agrupamento de itens, empilhamento, compatibilidade e rastreabilidade individual; desenhar contratos e ADR antes de mudar a engine.
3. **Planejamento e 3D:** manter o 3D destacado, expansível e útil na revisão das distribuições; avaliar melhor comparação entre caminhões sem confundir sugestões do Loxi com simulação/otimização real.
4. **Loxi operacional:** avançar de consultas para **ações autorizadas confirmáveis** somente após #368, com isolamento, auditoria, consentimento explícito e rollback/compensação quando cabível.
5. **Confiabilidade e pré-produção:** concluir os itens de qualidade, performance, provider de comunicação, e-mail, anexos e deploy seguro acima, sem declarar ambiente de produção validado sem evidências.

Priorizar este backlog juntamente com o planejamento da próxima versão; a ordem e a release-alvo ainda precisam de decisão formal.

---

# v1.4.0 — LoadX Platform: SaaS multiempresa e licenciamento

**Decisão de produto (14/11/2026):** o LoadX passa a ser uma plataforma SaaS autônoma, proprietária de identidade global, organizações, administração central, catálogo, licenças, billing e entitlements.

- [Planejamento técnico v1.4.0](v1.4.0/00-visao-geral.md)
- [Épico #439](https://github.com/RennaN-C/loadx-smart-logistics/issues/439) e Issues #440–#447
- [ADR-049](../decisions/ADR-049-multiempresa-organizacoes-isolamento.md) — tenancy e isolamento
- [ADR-050](../decisions/ADR-050-control-plane-comercial-billing-entitlements.md) — plataforma autônoma e modular
- [ADR-051](../decisions/ADR-051-gateway-pagamentos-port-adapter.md) — pagamentos com port/adapters

## Núcleo LoadX Platform

- Conta global, autenticação, MFA, sessão e recuperação.
- Organizações, solicitação de cadastro, aprovação pelo proprietário e memberships.
- Painel geral exclusivo para o proprietário do LoadX.
- Planos versionados, módulos incluídos/adicionais, limites e licenças.
- Assinaturas, cobranças automáticas, gateways, webhooks e conciliação.
- Bloqueio imediato ao fim do período já pago; dados preservados.
- Auditoria, permissões de plataforma e proteção de dados entre empresas.

## Produto comercial inicial: LoadX Logistics

O domínio atual passa a ser isolado por organização, preservando pedidos, produtos, clientes, frota, motoristas, planejamento, otimizador, carregamento, viagens, entregas, ocorrências, relatórios, anexos e Loxi.

A visualização 3D **permanece integrada e destacada** dentro da experiência de planejamento de cargas. Não separar o visualizador das regras físicas do otimizador de maneira prematura.

## Evolução de módulos e nichos

Visão de longo prazo:
- **LoadX Platform:** núcleo SaaS compartilhado;
- **LoadX Logistics:** primeiro módulo setorial;
- **LoadX 3D:** eventual capacidade compartilhada de visualização e simulação 3D, com contratos próprios, reutilizável por mais de um módulo;
- **Outros módulos setoriais:** somente após validação de necessidade e regras próprias.

Esses módulos adicionais não integram o escopo de implementação da v1.4.0. A arquitetura deve permitir sua introdução futura com os mesmos usuários, empresas, permissões, contratos e pagamentos. Manter monólito modular e evitar microserviços por antecipação.

## Plano de execução

| Issue | Escopo | Responsável |
|---|---|---|
| #440 | Fechar contratos núcleo SaaS e comparar gateways | Rennan |
| #441 | Organização, membership, isolamento e migração legada | Rennan |
| #442 | Solicitação, aprovação e convite de empresas | Rennan |
| #443 | Planos, catálogo de módulos, adicionais e limites | Rennan |
| #444 | Assinaturas, licenças, vencimento e entitlements | Rennan |
| #445 | Gateway, checkout, webhook, idempotência e conciliação | Rennan |
| #446 | Painel do proprietário e portal financeiro | A atribuir |
| #447 | Testes cross-tenant, cobrança e piloto | A atribuir |

A Issue #430 do João Weber, sobre desempenho do otimizador, permanece independente.

## Gates antes da publicação

- Inventário de schema, FKs, unicidades, rotas, workers e dados legados.
- Bootstrap seguro da única conta proprietária, com recuperação excepcional auditada.
- Backfill e migração auditáveis para organização legada.
- Testes negativos de acesso cruzado por API, jobs, anexos, auditoria e Loxi.
- Seleção do primeiro gateway após condições comerciais e Sandbox.
- Testes de webhook, reconciliação e vencimento imediato.
- Piloto isolado com duas organizações e dados sintéticos.
- Sem release, cobrança real ou alteração em produção antes de validação e autorização.

A plataforma e seus módulos devem manter identidade visual e experiência unificadas, mesmo quando a navegação e permissões variem por módulo.

---

# v1.5.0 — Rastreamento e acompanhamento em tempo real

`RECOMENDAÇÃO`: evolução destinada à localização de viagens, ETA e
acompanhamento operacional.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Modelo de localização, histórico e API de posição |
| A definir | João | ETA, risco de atraso e previsão operacional |
| A definir | Marlon | Mapa operacional e acompanhamento para cliente |
| A definir | Marcelo | Ingestão de localização, adaptador externo e notificações |

`DECISÃO NECESSÁRIA`: antes da implementação, definir a fonte da localização.
As opções podem incluir dispositivo móvel, plataforma de telemetria, equipamento
GPS ou provedor externo.

O domínio de localização não deve depender diretamente de um fornecedor
específico.

`PENDENTE DE DEFINIÇÃO`: frequência de atualização, retenção do histórico,
precisão necessária, geofencing, privacidade e tratamento de perda de sinal.

---

# v1.6.0 — Roteirização e custos logísticos

`RECOMENDAÇÃO`: evolução destinada ao planejamento geográfico e econômico das
viagens.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Contratos de rota, trechos, custos e persistência |
| A definir | João | Algoritmo de roteirização e modelo de custos |
| A definir | Marlon | Planejador visual e dashboard de eficiência |
| A definir | Marcelo | Adaptador geográfico externo, alertas e relatórios |

Objetivos possíveis:

- distância;
- duração;
- janelas de entrega;
- combustível;
- pedágio;
- capacidade;
- quantidade de veículos;
- custo estimado da operação.

`DECISÃO NECESSÁRIA`: definir se o núcleo utilizará cálculo próprio, provedor
geográfico externo ou composição dos dois.

`CONFIRMADO`: sequência de carregamento e sequência geográfica de entregas são
problemas diferentes e não devem ser misturados.

---
# v1.7.0 — Inteligência artificial avançada

`RECOMENDAÇÃO`: ampliar a IA **além do Loxi consultivo da v1.3.0**. Conversa contextual, Groq e consultas read-only já estão contempladas na v1.3.0; esta etapa futura trata previsões, recomendações avançadas e ações operacionais efetivamente autorizadas, com escopo/versão a decidir. A Issue #368 pode ser priorizada antes da v1.7.0 mediante planejamento próprio.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Segurança, autorização e contratos das ações assistidas por IA |
| A definir | João | Interpretação estruturada, previsão e recomendações |
| A definir | Marlon | Interface do assistente e explicações |
| A definir | Marcelo | Adapter do provider externo, integração com WhatsApp e observabilidade |

## Regra arquitetural permanente

`CONFIRMADO`: IA generativa não substitui validações físicas ou regras críticas.

A IA pode:

- interpretar;
- explicar;
- resumir;
- recomendar;
- prever;
- auxiliar decisões.

A IA não pode:

- aceitar carga fisicamente inválida;
- ignorar peso, colisão, apoio ou rotação;
- contornar autorização;
- criar transições inexistentes;
- escrever diretamente no banco;
- executar ação operacional sem passar pelo service responsável.

`CONFIRMADO`: a v1.3.0 possui adapter Groq configurável, limites e fallback. `DECISÃO NECESSÁRIA`: critérios e eventual provider para **novos usos** (previsões, ações), tratamento de dados, observabilidade, orçamento e controles por tenant se a v1.4.0 for aprovada.

---

# v1.8.0 — Visão computacional e análise física avançada

`RECOMENDAÇÃO`: adicionar apoio visual e físico à conferência sem substituir o
núcleo determinístico.

## Trilha A — Visão computacional

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Contrato de eventos, evidências e persistência |
| A definir | João | Reconhecimento e associação de volumes |
| A definir | Marlon | Conferência e guia visual |
| A definir | Marcelo | Pipeline de mídia, armazenamento, segurança e testes |

## Trilha B — Análise de peso por eixo

`DECISÃO NECESSÁRIA`: tratar peso por eixo como problema independente da visão
computacional.

Antes da implementação devem ser definidos:

- geometria e posição dos eixos do veículo;
- centro de massa relevante;
- limites por eixo;
- origem dos dados;
- precisão;
- regra física;
- efeito sobre aprovação do plano.

`RISCO IDENTIFICADO`: juntar peso por eixo e reconhecimento de câmera em uma
única regra de domínio criaria acoplamento desnecessário entre problemas
distintos.

---

# Marco móvel — v2.0.0 candidata

## Objetivo de produto

Levar a operação do LoadX para o campo por meio de uma experiência móvel.

Capacidades candidatas:

- aplicativo para motorista;
- operação de entregas em dispositivo móvel;
- captura de evidências;
- comunicação e notificações;
- suporte a conectividade instável;
- sincronização;
- uso de câmera e sensores;
- realidade aumentada para apoio ao carregamento.

`DECISÃO NECESSÁRIA`: confirmar o número da versão antes do planejamento
formal.

Se a plataforma móvel puder ser adicionada mantendo compatibilidade com os
contratos públicos existentes, o incremento correto pelo SemVer deverá ser
MINOR, por exemplo v1.9.0.

A denominação v2.0.0 somente será adotada quando houver breaking change que
justifique MAJOR.

---

# Sequência planejada de evolução

A ordem abaixo representa direção de produto, não dependência técnica automática:

v1.0.0 → v1.1.0 → v1.2.0 → **v1.3.0** → v1.4.0 → v1.5.0 → v1.6.0 → v1.7.0 → v1.8.0 → marco móvel

Uma versão pode começar a ser planejada enquanto a anterior ainda está em
validação, mas uma implementação não deve depender de contratos ainda instáveis.

---

# Gates para iniciar uma nova versão

`RECOMENDAÇÃO`: antes de abrir o desenvolvimento de uma versão funcional:

1. revisar este roadmap;
2. confirmar o próximo número SemVer;
3. verificar a próxima numeração de OC realmente disponível;
4. abrir milestone da versão;
5. criar planejamento específico;
6. criar as Issues;
7. definir responsáveis;
8. definir dependências;
9. registrar decisões e ADRs necessárias;
10. adicionar Issues ao Project;
11. liberar somente ocorrências sem bloqueadores;
12. seguir o fluxo Git aprovado para aquela release.

---

# Critérios de encerramento de uma versão

Uma versão somente deve ser considerada pronta para promoção quando:

- OCs planejadas estiverem concluídas ou explicitamente removidas do escopo;
- contratos estiverem documentados;
- migrations estiverem consistentes;
- testes mínimos e suíte integrada estiverem verdes;
- CI e segurança estiverem aprovadas;
- riscos conhecidos estiverem documentados;
- documentação estiver atualizada;
- fluxos críticos tiverem sido validados de ponta a ponta.

---

# Princípios permanentes

1. Backend protege as regras; frontend não substitui autorização.
2. Regras críticas permanecem determinísticas.
3. Integrações externas ficam atrás de adapters.
4. Concorrência é tratada no backend e no banco.
5. Mudança estrutural exige documentação prévia.
6. Nova regra de domínio pode exigir ADR.
7. Cada OC possui Issue própria.
8. Cada mudança entra por Pull Request.
9. Códigos públicos não mudam silenciosamente.
10. Planejamento futuro não é autorização automática de implementação.
11. Numeração de OC não é reutilizada.
12. O SemVer da release é decidido pelo tipo real da mudança.
13. O LoadX será proprietário de identidade global, organizações, licenciamento, billing e administração geral da plataforma.
14. Módulos setoriais futuros utilizarão o mesmo núcleo SaaS e terão contratos de domínio e permissões próprias.

---

# Estado das versões e próximo ciclo

**Versões anteriores já publicadas:** [v1.0.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.0.0), [v1.1.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.1.0) e [v1.2.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0) em 26/10/2026.

**Código desta versão:** [v1.3.0 / PR #388](https://github.com/RennaN-C/loadx-smart-logistics/pull/388) — Loxi e planejamento/3D; conferir publicação em [Releases](https://github.com/RennaN-C/loadx-smart-logistics/releases). **Próximo ciclo funcional:** v1.4.0 — LoadX Platform multiempresa, licenciamento e cobrança. `CONFIRMADO` (19/11/2026): implementação incremental autorizada, com fundação e G01–G05-B integrados na base `2bef6071`; G05-C em andamento, G06–G11 e núcleo comercial pendentes. Consulte a [matriz auditada](v1.4.0/00-visao-geral.md) para evidências e dependências. A segunda organização operacional continua desabilitada; merges com impacto remoto, gateway real e lançamento comercial dependem de aprovação explícita. O backlog transversal (escala ≥1.000 volumes, embalagens, ações do Loxi e confiabilidade) exige critérios e validação próprios.

**Manutenção:** acompanhar as Issues ativas listadas na seção v1.3.0, sobretudo #268, #256, #254 e #382. Não reescrever tags anteriores; cada correção exige classificação SemVer adequada e nova validação.

**Implantação externa:** publicação do código não equivale a homologação de provedores, storage ou workers remotos. A ativação de WhatsApp Business real e a infraestrutura de produção devem ser aprovadas separadamente.
