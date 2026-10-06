# Roadmap de versões — LoadX Smart Logistics

## Status e governança deste documento

`CONFIRMADO`: este documento é a referência canônica para o planejamento de
releases posteriores à v1.1.0.

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

`CONFIRMADO`: versões PATCH não são pré-planejadas neste roadmap. Elas surgem
quando uma versão já publicada exige correção.

`DECISÃO NECESSÁRIA`: o marco atualmente chamado de v2.0.0 somente deverá usar
esse número se introduzir mudança incompatível que justifique incremento de
MAJOR. Se a plataforma móvel puder ser adicionada de forma compatível, o número
correto continuará a sequência MINOR, por exemplo v1.8.0.

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
#122–#133, #136–#141 e #144–#159. O escopo reúne comunicação real, administração,
operação multi-caminhão, gestão operacional, segurança, frota, cadastros,
auditoria, confiabilidade de integrações e experiência de uso.

Esses números somente representam trabalho executável enquanto as respectivas
Issues permanecerem aprovadas, atribuídas e vinculadas ao planejamento da versão.

`CONFIRMADO`: números posteriores à OC112 não ficam reservados antecipadamente.
A numeração da v1.3.0 em diante será definida no momento do planejamento de cada
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

`CONFIRMADO`: versão-base do produto.

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

# v1.2.0 — Consolidação do produto e operação avançada

## Objetivo

`CONFIRMADO`: a v1.2.0 concentra a maior etapa de consolidação funcional do LoadX
antes da evolução multiempresa. O objetivo é fechar lacunas de administração,
segurança, operação, frota, cadastros, auditoria, integrações e experiência de uso,
sem retirar a autoridade das regras de domínio do backend.

`CONFIRMADO`: a v1.2.0 continua **monoempresa**. A evolução para várias empresas
isoladas pertence somente ao roadmap da v1.3.0.

## Planejamento aprovado

| OC | Issue | Responsável | Entrega planejada |
|---|---:|---|---|
| OC79 | #122 | Rennan | Segurança, autorização e idempotência de comandos externos |
| OC80 | #123 | Rennan | Contrato de evidências e comprovante de entrega |
| OC81 | #124 | Marlon | Interface de comprovante e comunicação operacional |
| OC82 | #125 | Marcelo | Adaptador real para WhatsApp Business |
| OC83 | #126 | Marcelo | Webhook, recebimento de mensagens e mídia |
| OC84 | #127 | Marcelo | Notificações operacionais reais |
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

Ao encerrar a v1.2.0, o LoadX deverá:

- possuir administração interna, configurações, gestão de usuários, perfil e segurança de conta;
- suportar comunicação real, evidências, anexos e integrações resilientes;
- operar carga em um ou vários caminhões preservando rastreabilidade;
- oferecer central operacional, agenda, exceções, reentrega e cancelamento;
- possuir manutenção, documentos e vencimentos de frota e motoristas;
- permitir múltiplos endereços por cliente e importação/arquivamento de cadastros;
- oferecer busca por módulo e busca global no servidor;
- apresentar auditoria, linha do tempo, notificações internas e relatórios gerenciais;
- expor saúde das integrações ao ADMIN sem revelar segredos;
- permitir perfis administrativos flexíveis sem retirar a autorização do backend.

---
# v1.3.0 — Plataforma multiempresa

`RECOMENDAÇÃO`: transformar o LoadX monoempresa em uma plataforma capaz de atender
várias empresas no mesmo produto com isolamento obrigatório de dados e administração.

`CONFIRMADO`: esta seção é **roadmap**, não planejamento executável. Nenhuma OC ou
Issue funcional da v1.3.0 foi criada ou reservada.

## Direção arquitetural

- entidade de empresa/tenant como fronteira de isolamento;
- associação explícita de usuários à empresa ou empresas autorizadas;
- escopo de empresa em clientes, motoristas, caminhões, produtos, pedidos, planos, carregamentos, viagens, entregas, ocorrências, relatórios, evidências e configurações;
- consultas e comandos sempre resolvidos no contexto da empresa autenticada;
- chaves e unicidades que não permitam colisão indevida entre empresas;
- testes negativos obrigatórios impedindo acesso cruzado entre tenants;
- separação entre **ADMIN da empresa** e um futuro **SUPERADMIN da plataforma**;
- configurações, integrações e identidade visual por empresa quando aprovadas;
- migration/backfill dos dados monoempresa existentes para a empresa inicial.

## Distribuição candidata

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Modelo de tenant, migrations, autorização e isolamento de dados |
| A definir | João | Revisão de consultas, índices e desempenho com escopo por empresa |
| A definir | Marlon | Seleção/contexto de empresa e administração visual |
| A definir | Marcelo | Integrações, auditoria e observabilidade isoladas por empresa |

`DECISÃO NECESSÁRIA`: antes da implementação, definir se um usuário poderá
pertencer a uma ou várias empresas e como será feita a troca de contexto.

`DECISÃO NECESSÁRIA`: definir o papel do SUPERADMIN, criação/ativação de empresas,
limites de suporte e quais ações ficam disponíveis fora do contexto de uma empresa.

`RECOMENDAÇÃO`: iniciar com banco PostgreSQL compartilhado e coluna de tenant nas
entidades de negócio, mantendo a arquitetura preparada para estratégias de
isolamento mais fortes no futuro caso requisitos comerciais ou regulatórios exijam.

`PENDENTE DE DEFINIÇÃO`: licenciamento, planos, cobrança, limites por empresa,
customização de domínio e eventual segregação física de banco.

---

# v1.4.0 — Rastreamento e acompanhamento em tempo real

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

# v1.5.0 — Roteirização e custos logísticos

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
# v1.6.0 — Inteligência artificial avançada

`RECOMENDAÇÃO`: ampliar o uso de IA para interpretação, explicação, previsão e
apoio operacional.

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

`DECISÃO NECESSÁRIA`: escolha de provider externo, política de dados,
timeouts, fallback, orçamento, observabilidade e limites de uso.

---

# v1.7.0 — Visão computacional e análise física avançada

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
MINOR, por exemplo v1.8.0.

A denominação v2.0.0 somente será adotada quando houver breaking change que
justifique MAJOR.

---

# Sequência planejada de evolução

A ordem abaixo representa direção de produto, não dependência técnica automática:

v1.0.0 → v1.1.0 → v1.2.0 → v1.3.0 → v1.4.0 → v1.5.0 → v1.6.0 → v1.7.0 → marco móvel

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

---

# Ciclo atual — v1.2.0

`CONFIRMADO`: a v1.1.0 foi publicada. O próximo ciclo funcional é a v1.2.0,
com OC79–OC112 e Issues #122–#133, #136–#141 e #144–#159.

Antes da implementação:

1. criar/confirmar o milestone `v1.2.0`;
2. vincular #122–#133, #136–#141 e #144–#159 ao milestone;
3. adicionar #122–#133, #136–#141 e #144–#159 ao Project `LoadX — Desenvolvimento`;
4. configurar os status iniciais conforme as dependências;
5. liberar somente as OCs sem bloqueadores;
6. iniciar cada ocorrência em branch própria a partir de `desenvolvimento`;
7. integrar por PR e validar CI, segurança, contratos e documentação.
