# Feature: deliveries

Acompanhamento de viagem e entregas (OC34). Consome `GET /trips`, `POST /trips`, `GET /trips/{id}`,
`PATCH /trips/{id}/status` e `PATCH /deliveries/{id}/status`.

## O que existe hoje

- `pages/TripPage.tsx` (+ `.css`): a rota `/trips/:tripId` — situação da viagem, paradas na ordem da
  rota e as ações que avançam o ciclo.
- `components/CreateTripAction.tsx`: cria a viagem a partir de um plano de carga **aprovado**.
- `components/tripLabels.ts`: rótulos de situação e o verbo de cada ação.
- `components/tripsErrorMessages.ts`: tradução dos 15 códigos de erro do módulo.
- `api/tripsApi.ts`: mapeamento snake_case ↔ camelCase.

## Ciclos de mão única

O backend não permite voltar atrás nem pular etapa (`TRIP_STATUS_TRANSITIONS` e
`DELIVERY_STATUS_TRANSITIONS`):

| viagem | entrega |
|---|---|
| `SCHEDULED` → `IN_ROUTE` → `FINISHED` | `PENDING` → `IN_DELIVERY` → `DELIVERED` |

Por isso a tela mostra **um botão só**, com o verbo da próxima etapa ("Iniciar viagem", "Confirmar
entrega") em vez de um seletor de situação: não há escolha a fazer.

Duas travas do backend viram estado visível na tela, não erro depois do clique:

- entrega só se movimenta com a viagem `IN_ROUTE` (`DELIVERY_TRIP_NOT_IN_ROUTE`) — antes disso os
  botões ficam desabilitados e a tela explica;
- viagem só finaliza com todas as entregas concluídas (`TRIP_DELIVERIES_NOT_FINISHED`) — o botão fica
  desabilitado enquanto houver parada em aberto.

## Como se chega aqui

Por dois caminhos.

**Criando**, a partir do plano de carga aprovado: `PlanSummary` mostra "Criar viagem" quando o plano
está `APPROVED`, e depois de criada a viagem vive em `/trips/:tripId`.

**Pela lista**, com `GET /trips` paginado. `ADMIN` e `LOGISTICS_MANAGER` veem todas; `DRIVER` recebe
**somente as dele** — o recorte é feito em `deliveries/service.py`, não no frontend. Repetir esse
filtro aqui seria duplicar no cliente uma regra de acesso que já é aplicada onde importa.

`CONFIRMADO`: o `DRIVER` tinha ficado sem porta de entrada enquanto a listagem não existia, e o
painel dele abria com contadores que respondiam 403. Agora a tela inicial do motorista lista as
viagens dele, com carregando, vazio, erro e link para cada uma.

## Disponibilidade do motorista (OC72)

`CreateTripAction` continua oferecendo somente motoristas ativos e agora
consulta `GET /drivers/operational-status` para saber a situação operacional.
O frontend não cruza viagens nem recalcula conflito: usa diretamente
`available` e `has_operation_conflict` produzidos pela OC67.

Motorista com conflito aparece como **em operação** e fica desabilitado, porque
`create_trip` já chama `DriverService.ensure_no_operation_conflict` e rejeita
essa escolha no backend. Se a consulta de disponibilidade falhar, a tela avisa
que não conseguiu confirmar o estado e deixa a validação final para o servidor,
que continua sendo a fonte de verdade.

## Carregamento e início da viagem

`CONFIRMADO`: o backend possui carregamento persistido, checklist e finalização.
`LoadingReferenceService` libera `SCHEDULED -> IN_ROUTE` quando a sessão do
mesmo plano está `FINISHED`; ausência ou incompletude retorna
`TRIP_LOADING_NOT_FINISHED`. O fluxo positivo está coberto por
`backend/tests/e2e/test_complete_flow.py`.

`CONFIRMADO`: `components/tripsErrorMessages.ts` orienta o usuário a finalizar
a sessão de carregamento antes de iniciar a viagem quando o backend retorna
`TRIP_LOADING_NOT_FINISHED`.

`CONFIRMADO`: `PATCH /deliveries/{id}/status` retorna somente `DeliveryRead`.
`changeDeliveryStatus` interpreta essa resposta como `DeliveryDto`, mapeia a
entrega e usa seu `trip_id` para recarregar `GET /trips/{trip_id}`. O hook
`useTripPage` substitui o estado pela viagem completa desse GET, sem reconstrução
parcial no navegador. A assinatura pública do adapter continua `Promise<Trip>`;
`TripPage` permanece compatível e é seu único consumidor de produção.

`CONFIRMADO`: falha no PATCH não dispara GET. Falha no GET posterior propaga o
erro para a tela, preserva o último estado conhecido e não repete automaticamente
o PATCH; a alteração pode já estar persistida e uma recarga da página consulta
o estado atual. Os testes `api/tripsApi.test.ts` e
`pages/TripPage.integration.test.tsx` cobrem contratos, erros e o ciclo
`PENDING -> IN_DELIVERY -> DELIVERED` com adapter e hook reais.

## Permissões

Ler: `ADMIN`, `LOGISTICS_MANAGER` e `DRIVER`. Operar (mover viagem e entregas):
`LOGISTICS_MANAGER` e `DRIVER`. Criar viagem: só `LOGISTICS_MANAGER`.

O motorista só enxerga a própria viagem — o backend confere pelo vínculo `users.driver_id`, criado na
`OC09`. A tela não tenta replicar essa checagem; um acesso indevido volta `AUTH_FORBIDDEN` e a
mensagem diz que a viagem não é sua.

## Comprovante e evidências (OC78 / OC80 / OC81)

`CONFIRMADO`: são dois contratos ENCADEADOS. O comprovante nasce da conclusão
da entrega e identifica o HISTÓRICO dela — não é um arquivo, não tem foto nem
assinatura embutida. A evidência se pendura nesse comprovante. Por isso o
painel carrega o comprovante primeiro: sem ele não há onde anexar, e o backend
responde `DELIVERY_RECEIPT_NOT_AVAILABLE`.

Chega-se pelo botão **Comprovante** de cada parada, que só aparece em entrega
`DELIVERED` — antes disso não há o que mostrar.

### A chave de intenção é o que impede duplicata

`CONFIRMADO`: o registro leva `event_id`, e o backend tem
`UNIQUE (recorded_by, event_id)`. Numa falha de rede, repetir com a MESMA chave
devolve o registro original em vez de criar uma segunda evidência igual.

Por isso o arquivo escolhido só é descartado depois de um registro
bem-sucedido, e a chave vive junto dele: o botão vira "Tentar novamente" e
reenvia com a mesma chave. Depois da primeira tentativa, o tipo é congelado. Chave nova somente por uma
nova seleção explícita de arquivo; mudar o tipo antes do primeiro envio também
cria nova intenção. Reaproveitar a chave para outros bytes/tipo daria
`EVIDENCE_IDENTITY_CONFLICT`.

### Validação local não substitui a do servidor

PNG/JPEG e 5 MiB são conferidos antes de enviar (`services/imageFile.ts`,
compartilhado com os anexos da OC110), para a pessoa não esperar o upload de um
arquivo grande só para receber recusa. O limite de 20 milhões de pixels fica de
fora de propósito: só se conhece decodificando a imagem. O backend revalida
pelos BYTES, não pelo tipo que o navegador declarou.

A recusa local não passa pelo mapa de códigos da API — mandá-la para lá
transformaria "Selecione PNG/JPEG de até 5 MiB" em "erro inesperado".

### Revogação

É lógica e definitiva: preserva metadados e responsável, bloqueia o download e
não tem reativação nem substituição de arquivo. Por isso a tela confirma antes.

### Permissões

`CONFIRMADO`: `ADMIN`, `LOGISTICS_MANAGER` e `DRIVER` leem e operam no nível de
perfil; o recorte por viagem (motorista só na própria) é do backend e não é
reproduzido aqui. `CHECKER` é negado.

### Comunicação operacional disponível

`CONFIRMADO`: a finalização coordenada da OC81 acrescenta
`GET /deliveries/{delivery_id}/communications`, consulta paginada de fatos reais
OC84/OC109. O backend seleciona somente `OCCURRENCE_REGISTERED` cuja ocorrência
possui exatamente o `delivery_id` e a viagem autorizada. Não varre notificações
pessoais e não atribui `TRIP_STARTED` ou ocorrência geral de viagem à entrega.

O botão **Comunicação** fica disponível nas paradas autorizadas, inclusive antes
da conclusão. A interface mostra estados reais da simulação e do processamento,
com carregamento, vazio, erro/retry e paginação. WHATSAPP_MOCK é apresentado como
**WhatsApp simulado**: sucesso não comprova envio, recebimento ou leitura Meta.
Não há conversa, envio livre, retry administrativo nem canal externo real.

`CONFIRMADO`: a consulta exige grants efetivos `loadx.deliveries.read` e
`loadx.occurrences.read`, ou motorista com `loadx.trips.own` ativo e vinculado à
viagem. A central pessoal OC103 permanece independente: consultar este painel
não marca notificações como lidas nem expõe destinatários/preferências alheias.

### Continuidade e consistência da interface

`CONFIRMADO`: evidências usam paginação server-side de vinte itens, permitindo
reencontrar registros além da primeira página. Falha ao atualizar a listagem não
apaga o comprovante consultado nem transforma um upload confirmado em falha.
Após falha sem confirmação, o tipo fica congelado e a mesma intenção, arquivo e
bytes são usados no retry. Selecionar outro arquivo inicia outro registro
explícito. Trocar a entrega remonta o painel e descarta respostas tardias; não
persiste imagens, tokens ou intenções em Web Storage.

`RISCO IDENTIFICADO`: se a conexão falhar após o commit, a UI não afirma que nada
foi gravado. Consultar a lista ou repetir a mesma intenção permite recuperar o
resultado. Fechar a tela descarta o rascunho local; não há upload em background
ou promessa de retomada de arquivo após F5. O backend continua autoritativo.

`CONFIRMADO`: os commits originais de Marlon foram reaproveitados com autoria e
referência de cherry-pick; sua branch não foi sobrescrita. Não há migration,
nova dependência, envio Meta ou alteração de domínio da OC90.

## Central operacional — auditoria UI01 / #276

`CONFIRMADO`: Carregamentos e Entregas reutilizam FormField, StatusPill e
paginação server-side existentes. Referências curtas distinguem registros;
links preservam UUID completo e nomes acessíveis por recurso. Carregamentos
reutiliza os rótulos do detalhe da conferência. Filtros reiniciam a página,
loading/erro/retry/vazio são explícitos e o total vem da API, sem reconstruir
estados de domínio no navegador. Tokens, RBAC e contratos HTTP preservados.
Evidências: [UI01](../../../../docs/evidencias/qa-v12-pentest/ui-lote1.md).
