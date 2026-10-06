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

`RECOMENDAÇÃO`: a próxima versão, v1.2.0, reserva a faixa OC79–OC84 para seu
planejamento inicial.

Esses números somente se tornam ocorrências executáveis quando as respectivas
Issues forem criadas e aprovadas.

`CONFIRMADO`: números posteriores à OC84 não ficam reservados antecipadamente.
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

`CONFIRMADO`: versão atualmente em desenvolvimento.

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

# v1.2.0 — Comunicação real e comprovante de entrega

## Objetivo

Transformar fluxos simulados de comunicação e evidência em operações externas
reais, auditáveis, idempotentes e protegidas.

## Planejamento inicial

| OC | Responsável | Entrega planejada |
|---|---|---|
| **OC79** | **Rennan** | Segurança, autenticação, autorização e idempotência de comandos externos |
| **OC80** | **Rennan** | Contrato de evidências e comprovante de entrega |
| **OC81** | Marlon | Interface de comprovante e comunicação operacional |
| **OC82** | Marcelo | Adapter real para WhatsApp Business |
| **OC83** | Marcelo | Webhook, recebimento de mensagens e mídia |
| **OC84** | Marcelo | Notificações operacionais reais |

`PENDENTE DE DEFINIÇÃO`: dependências exatas entre OC79–OC84 serão definidas nas
Issues da versão.

`DECISÃO NECESSÁRIA`: definir política de retenção, armazenamento, acesso,
proteção e remoção das evidências de entrega antes de implementar storage real.

`CONFIRMADO`: mensagens externas não escrevem diretamente no banco. Qualquer
ação operacional passa pelos services e regras de domínio existentes.

## Resultado esperado

O sistema poderá enviar e receber comunicações reais e registrar evidências de
entrega sem contornar autenticação, autorização ou regras de negócio.

---

# v1.3.0 — Rastreamento e acompanhamento em tempo real

`RECOMENDAÇÃO`: evolução destinada à localização de viagens, ETA e
acompanhamento operacional.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Modelo de localização, histórico e API de posição |
| A definir | João | ETA, risco de atraso e previsão operacional |
| A definir | Marlon | Mapa operacional e acompanhamento para cliente |
| A definir | Marcelo | Ingestão de localização, adapter externo e notificações |

`DECISÃO NECESSÁRIA`: antes da implementação, definir a fonte da localização.
As opções podem incluir dispositivo móvel, plataforma de telemetria, equipamento
GPS ou provider externo.

O domínio de localização não deve depender diretamente de um fornecedor
específico.

`PENDENTE DE DEFINIÇÃO`: frequência de atualização, retenção do histórico,
precisão necessária, geofencing, privacidade e tratamento de perda de sinal.

---

# v1.4.0 — Roteirização e custos logísticos

`RECOMENDAÇÃO`: evolução destinada ao planejamento geográfico e econômico das
viagens.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Contratos de rota, trechos, custos e persistência |
| A definir | João | Algoritmo de roteirização e modelo de custos |
| A definir | Marlon | Planejador visual e dashboard de eficiência |
| A definir | Marcelo | Adapter geográfico externo, alertas e relatórios |

Objetivos possíveis:

- distância;
- duração;
- janelas de entrega;
- combustível;
- pedágio;
- capacidade;
- quantidade de veículos;
- custo estimado da operação.

`DECISÃO NECESSÁRIA`: definir se o núcleo utilizará cálculo próprio, provider
geográfico externo ou composição dos dois.

`CONFIRMADO`: sequência de carregamento e sequência geográfica de entregas são
problemas diferentes e não devem ser misturados.

---

# v1.5.0 — Otimização global da frota e múltiplos caminhões

`RECOMENDAÇÃO`: permitir que uma mesma necessidade logística seja distribuída
entre mais de um veículo.

| OC | Responsável principal | Capacidade planejada |
|---|---|---|
| A definir | **Rennan** | Modelo de dados, cardinalidades e regras transacionais multi-veículo |
| A definir | João | Distribuição de volumes e otimização global da frota |
| A definir | Marlon | Planejamento multi-veículo no frontend |
| A definir | Marcelo | Auditoria, relatórios e testes E2E do fluxo |

Objetivos de otimização candidatos, nesta ordem:

1. completar integralmente a carga;
2. minimizar a quantidade de veículos;
3. respeitar conflitos e disponibilidade;
4. considerar eficiência de ocupação e capacidade.

`DECISÃO NECESSÁRIA`: nenhuma implementação multi-veículo deve começar antes de
uma ADR específica definir:

- cardinalidade entre pedido, plano, viagem e entrega;
- rastreabilidade por volume;
- aprovação de planos parciais;
- divisão e recomposição de entregas;
- histórico;
- estratégia de migration;
- compatibilidade dos contratos existentes.

`RISCO IDENTIFICADO`: esta versão altera premissas centrais do modelo atual e
tem potencial de quebrar contratos se for implementada sem essa definição.

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

# Próximo ciclo

Enquanto a v1.1.0 estiver aberta:

- finalizar as OCs restantes;
- validar integração da versão;
- evitar incluir funcionalidades da v1.2.0 em PRs da v1.1.0;
- registrar novas descobertas neste roadmap ou em documentação específica.

Após a conclusão da v1.1.0:

1. confirmar o fechamento da release;
2. abrir o milestone v1.2.0;
3. criar as Issues OC79–OC84;
4. detalhar critérios de aceite;
5. definir dependências;
6. adicionar as OCs ao Project;
7. liberar as primeiras OCs sem bloqueadores.
