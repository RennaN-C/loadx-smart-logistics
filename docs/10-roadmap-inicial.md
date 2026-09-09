# Roadmap inicial

`CONFIRMADO`: as sprints abaixo preservam a sequência original de construção do
MVP. As entregas presentes na preparação da v1.0.0 estão no
[Changelog](../CHANGELOG.md); a lista de sprints não é uma lista de pendências.

`CONFIRMADO`: a numeração de referência para ocorrências passa a ser a do documento-base anexado: `OC01` a `OC48`.

`RISCO IDENTIFICADO`: versões anteriores deste documento usavam outra sequência `OC-01` a `OC-30`. Para evitar conflito entre os 4 desenvolvedores, novas issues e PRs devem usar `OCXX` conforme `docs/07-divisao-equipe.md`.

## Sprint 0: fundação técnica

Objetivo: deixar ambiente local, backend, frontend, banco e documentação mínima prontos para desenvolvimento integrado.

- `OC01`: configuração do projeto backend.
- `OC02`: criação e configuração do banco de dados.
- `OC23`: configuração do frontend.
- `OC48`: documentação inicial e guias de trabalho.

Entregável integrado:

- `docker compose up --build` sobe banco, backend e frontend.
- `/health` responde.
- Documentação principal está revisada.

## Sprint 1: cadastros, autenticação e contratos

Objetivo: permitir cadastro e consulta dos dados-base do MVP.

- `OC03`: autenticação e controle de acesso.
- `OC04`: cadastro de caminhões.
- `OC05`: cadastro de motoristas.
- `OC06`: cadastro de clientes.
- `OC07`: cadastro de produtos e volumes.
- `OC08`: cadastro de pedidos.
- `OC24`: tela de login.
- `OC26`: tela de caminhões.
- `OC27`: tela de produtos.
- `OC28`: tela de clientes e motoristas.
- `OC29`: tela de pedidos.

Entregável integrado:

- API de cadastros com testes mínimos.
- Telas consumindo API ou mocks alinhados ao contrato.

## Sprint 2: núcleo do planejamento

Objetivo: implementar o coração determinístico do LoadX.

- `OC11`: cálculo da capacidade do caminhão.
- `OC12`: cálculo do volume dos produtos.
- `OC13`: ordenação dos volumes.
- `OC14`: rotação dos volumes.
- `OC15`: posicionamento dos volumes.
- `OC16`: validação de colisões.
- `OC17`: validação de empilhamento.
- `OC18`: controle de peso.
- `OC19`: cálculo do aproveitamento.
- `OC20`: sequência de carregamento.
- `OC30`: tela de planejamento.

Entregável integrado:

- Endpoint de plano de carga retorna posições, rejeições, peso e ocupação.
- Testes unitários cobrem limites, colisões, rotação, peso e reprodutibilidade.

## Sprint 3: visualização, comparação e explicação

Objetivo: transformar o resultado do planejamento em experiência visual e justificável.

- `OC21`: comparação entre caminhões.
- `OC22`: explicação do planejamento com IA.
- `OC25`: dashboard.
- `OC31`: visualização 3D.
- `OC32`: interação com a visualização 3D.
- `OC33`: animação do carregamento.

Entregável integrado:

- Usuário calcula plano, visualiza carga em 3D e entende volumes posicionados/rejeitados.

`CONFIRMADO`: a `OC21` está concluída no MVP e compara de 2 a 10 caminhões por
execução, sem persistência, ranking, score ou escolha automática. A comparação
automática avançada permanece evolução futura.

`CONFIRMADO`: a `OC22` está concluída com port de IA, provider fake, timeout
configurável de 5 segundos por padrão e fallback determinístico. A IA explica
somente plano persistido e não valida, recalcula ou altera o resultado. O adapter
externo concreto permanece como integração do Desenvolvedor 4.

## Sprint 4: operação, WhatsApp e ocorrências

Objetivo: acompanhar carregamento, viagem, entregas e ocorrências.

- `OC09`: controle de viagens.
- `OC10`: histórico de status.
- `OC34`: tela de acompanhamento.
- `OC36`: configuração da integração com WhatsApp.
- `OC37`: comandos do motorista.
- `OC38`: interpretação de linguagem natural.
- `OC39`: atualização de status pelo WhatsApp.
- `OC40`: notificações automáticas.
- `OC41`: registro de ocorrências.
- `OC42`: envio de fotos.

Entregável integrado:

- Fluxo de carregamento/viagem atualiza status, registra histórico e aceita ocorrências por interface ou provider mock.

## Sprint 5: relatórios, testes finais e apresentação

Objetivo: fechar o MVP demonstrável de ponta a ponta.

- `OC35`: tela de indicadores e relatórios.
- `OC43`: relatório de carregamento.
- `OC44`: relatório de viagem.
- `OC45`: geração de relatório em PDF.
- `OC46`: testes da API.
- `OC47`: testes do fluxo completo.
- `OC48`: documentação final.

Entregável integrado:

- Fluxo completo testado: pedido, plano, 3D, carregamento, viagem, ocorrência e relatório.

## Critérios para avançar de sprint

- Contratos impactados atualizados em `docs/05`.
- Modelo de dados impactado atualizado em `docs/03`.
- Testes mínimos passando.
- PR revisado por outro desenvolvedor.
- Pendências registradas em `docs/11-riscos-pendencias.md` quando não forem resolvidas na sprint.

## Roadmap pós-v1.0.0

`CONFIRMADO`: os itens desta seção foram registrados na preparação da release
por solicitação da equipe e não foram implementados nesta tarefa.
`DECISÃO NECESSÁRIA`: cada evolução exige ocorrência, critérios de aceite e
aprovação antes de implementar; alterações de dados, contratos, estados,
integrações e escopo seguem as ADRs. Não há fornecedor, prazo ou nova dependência
aprovados por esta lista. Pendências técnicas existentes permanecem em
[docs/11](11-riscos-pendencias.md).

### Integração real com WhatsApp

`PENDENTE DE DEFINIÇÃO`: substituir o provider mock por integração real, com
envio e recebimento de mensagens para motorista, conferente e logística e
vínculo de cada mensagem ao usuário, viagem e entrega correspondentes. Definir
autenticação do webhook, assinatura, permissões e tratamento de duplicatas.

`CONFIRMADO`: hoje há simulador interno protegido em `/messages/interpret` e
`MockWhatsAppProvider`; não há webhook real. Notificações automáticas atuais
destinam-se ao motorista, após início da viagem via HTTP ou ocorrência registrada.

### IA aplicada às conversas operacionais

`PENDENTE DE DEFINIÇÃO`: interpretar mensagens naturais recebidas pelo WhatsApp
e convertê-las em intenções estruturadas, por exemplo: "já saí", "cheguei no
cliente", "já entreguei", "cliente não estava" e ocorrência durante a rota.
A interpretação externa deverá validar schema, identidade, autorização e estado.
A IA não deve escrever diretamente no banco: toda ação passa pelos services e
regras de domínio existentes.

`CONFIRMADO`: o MVP já interpreta comandos controlados no simulador e delega
ações ao `TripService`; isso não representa IA externa nem recepção real pelo
WhatsApp.

### Provider real de IA com Grok / xAI

`DECISÃO NECESSÁRIA`: avaliar Grok/xAI como provider externo futuro e implementar
adapter compatível com a port existente para explicação de planos. A port
`AIProvider` atual atende explicação; um contrato para conversas operacionais
precisa de definição própria. Manter provider fake nos testes, fallback
determinístico e impedir envio desnecessário de dados pessoais; explicação de
planos continua restrita ao contexto técnico já aprovado.

`CONFIRMADO`: esta release não adiciona SDK, chave, dependência ou integração
real com Grok/xAI ou outro provider externo.

### Atualização automática do fluxo via IA

`PENDENTE DE DEFINIÇÃO`: exemplo futuro, sujeito às validações existentes:

```text
Motorista: "já saí"
    -> interpretação da intenção
    -> identidade, autorização e validações de domínio
    -> viagem SCHEDULED -> IN_ROUTE (exige carregamento FINISHED)
    -> atualização do sistema e histórico pelos services
    -> notificação para logística e/ou cliente
```

Outras ações devem respeitar as transições existentes, inclusive idempotência.
`DECISÃO NECESSÁRIA`: exceções, atrasos e reentregas não autorizam criar estados
automaticamente; dependem de regras e contratos futuros.

### Distribuição de um pedido em múltiplos caminhões

`CONFIRMADO`: cada `LoadPlan` referencia um caminhão. A OC21 compara a carga
inteira em candidatos independentes e não distribui sobras. A aprovação rejeita
planos parciais; `deliveries.order_id` é único e um pedido gera no máximo uma
entrega no MVP (`ADR-014`, `ADR-022`).

`PENDENTE DE DEFINIÇÃO`: quando um pedido não couber em um caminhão, distribuir
os volumes restantes entre outros disponíveis e relacionar múltiplos planos ao
mesmo pedido/conjunto. Objetivos propostos, nesta ordem: completar 100% da carga,
minimizar a quantidade de caminhões e considerar eficiência de ocupação/capacidade.
`DECISÃO NECESSÁRIA`: rever aprovação, rastreabilidade por volume, entrega e
histórico antes de alterar as cardinalidades atuais. Não implementar agora.

### Disponibilidade de caminhões

`CONFIRMADO`: `Truck.active` controla habilitação cadastral; o planejamento
recusa caminhão inativo. `Trip` obtém o caminhão pelo plano, e a unicidade de
`trips.load_plan_id` impede duas viagens para o mesmo plano. Existem estados de
plano, carregamento e viagem, mas não há estado operacional persistido do caminhão
nem verificação de conflito entre viagens de planos diferentes do mesmo veículo.
Evidências: models de `trucks`/`deliveries` e services de `load_planning`/`deliveries`.

`PENDENTE DE DEFINIÇÃO`: impedir alocação conflitante e identificar caminhão em
uso, planejado, carregando, em rota ou disponível; avaliar manutenção.
`DECISÃO NECESSÁRIA`: definir reservas, intervalos, liberação e concorrência;
`active` não comprova disponibilidade em um período.

### Disponibilidade de motoristas

`CONFIRMADO`: a criação de viagem exige motorista ativo e bloqueia seu registro
durante a transação, mas não consulta viagens incompatíveis do mesmo motorista.
O vínculo único `users.driver_id` controla identidade, não agenda.

`PENDENTE DE DEFINIÇÃO`: evitar conflitos de motorista em viagens simultâneas
incompatíveis, com critérios de reserva e liberação aprovados.

### Monitoramento operacional da frota

`PENDENTE DE DEFINIÇÃO`: central operacional com visão de disponível, programado,
carregando, em rota, finalizado e manutenção. Esses rótulos são possibilidades
futuras, não novos estados aprovados para as entidades atuais.

### Rastreamento e localização

`PENDENTE DE DEFINIÇÃO`: avaliar GPS, localização em tempo real, ETA, geofencing
e previsão de chegada. Nenhum fornecedor está definido. GPS real e telemetria
continuam fora do escopo da v1.0.0.

### Status para o cliente

`PENDENTE DE DEFINIÇÃO`: oferecer acompanhamento de pedido planejado, carregado,
saiu para entrega, em rota, próximo da entrega, entregue e ocorrência/atraso
quando aplicável. Definir acesso e correspondência com os estados existentes,
sem expor dados pessoais ou operacionais desnecessários.

### Notificações reais ao cliente

`PENDENTE DE DEFINIÇÃO`: WhatsApp ou outro canal no início da viagem, entrega em
andamento, entrega concluída e atraso/ocorrência. Definir destinatários,
permissões, repetição e falhas de envio. Os avisos mock ao motorista existentes
não equivalem a notificações reais ao cliente.

### Comprovante de entrega

`PENDENTE DE DEFINIÇÃO`: foto, assinatura, responsável pelo recebimento,
data/hora, eventual localização e storage real de evidências.
`CONFIRMADO`: já há `delivered_at`; foto de ocorrência é somente referência
`mock://occurrences/<identificador>`, sem upload ou armazenamento binário.
`DECISÃO NECESSÁRIA`: definir retenção, acesso e proteção das evidências.

### QR Code / código de barras

`PENDENTE DE DEFINIÇÃO`: conferir volumes durante o carregamento por leitura de
código vinculado à identidade do volume, preservando o checklist e suas regras.

### Otimização de rota

`PENDENTE DE DEFINIÇÃO`: calcular a ordem das entregas por distância, prioridade
e janelas, além da disposição dentro do caminhão. A sequência informada nos
pedidos e usada hoje pelo otimizador não é roteirização geográfica.

### Custos logísticos

`PENDENTE DE DEFINIÇÃO`: considerar distância, combustível, pedágio, capacidade,
quantidade de veículos e custo estimado da operação. Valores monetários não
integram o modelo atual do MVP.

### Dashboard operacional

`CONFIRMADO`: existem contadores de cadastros/pedidos, lista de viagens do
motorista e indicadores de pedidos no frontend. Não há agregação geral de frota.

`PENDENTE DE DEFINIÇÃO`: ampliar indicadores para viagens em rota, entregas
concluídas, atrasos, ocorrências, utilização da frota, ocupação média, volumes
rejeitados e motivos de rejeição, com período e contratos de agregação definidos.

### Integração com ViaCEP

`PENDENTE DE DEFINIÇÃO`: consultar futuramente a API ViaCEP para facilitar e
padronizar endereços. Fluxo esperado: usuário informa CEP; frontend/backend
consulta a integração; quando disponível, preenche logradouro, bairro,
cidade/localidade, UF e demais informações úteis. O usuário completa número,
complemento e campos ausentes e pode corrigir os valores manualmente.

Requisitos futuros:

- validar formato do CEP e tratar CEP inexistente;
- tratar indisponibilidade e timeouts sem impedir inadequadamente o cadastro;
- permitir preenchimento e correção manual em caso de falha externa;
- definir cadastros abrangidos, avaliando inicialmente clientes;
- evitar duplicação da regra de endereço entre frontend e backend;
- centralizar a integração em adapter/service, sem espalhar HTTP pelo domínio;
- testar com mocks/fakes, sem depender da API real na suíte automatizada.

`DECISÃO NECESSÁRIA`: definir responsabilidade pela consulta e eventual evolução
do contrato de endereço antes de criar campos, endpoints ou migrations.
`CONFIRMADO`: ViaCEP foi somente documentado como evolução pós-v1.0.0; nenhuma
consulta, dependência ou integração foi implementada nesta preparação.

### Evolução do acesso a carregamento, ocorrências e relatórios

`CONFIRMADO`: o RBAC da v1.0.0 está descrito em `docs/04-regras-negocio.md`.
Os itens abaixo são futuros e não concedem acesso nesta release:

- `PENDENTE DE DEFINIÇÃO`: atribuição de carregamento a conferente e autorização
  por objeto para `CHECKER`; avaliar possível consulta de carregamento pelo
  `DRIVER`.
- `PENDENTE DE DEFINIÇÃO`: ocorrência vinculada ao carregamento, registro de
  ocorrência durante conferência e acesso do `CHECKER` nesse contexto.
- `PENDENTE DE DEFINIÇÃO`: relatório de carregamento para `CHECKER` e relatório
  da própria viagem para `DRIVER`.
