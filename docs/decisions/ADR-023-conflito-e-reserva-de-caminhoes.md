# ADR-023: conflito e reserva de caminhões

Status: aceita

## Contexto

A OC64 precisa impedir que o mesmo caminhão seja utilizado em operações
incompatíveis ao mesmo tempo.

O caminhão é associado ao fluxo operacional por meio de `LoadPlan.truck_id`.
Viagens não duplicam `truck_id`; o caminhão utilizado é determinado pelo
`load_plan_id`.

Planos aprovados também podem permanecer como histórico após recálculo.
Por isso, o estado `APPROVED` isoladamente não é suficiente para determinar
que um caminhão está ocupado.

## Decisão

- Planos `CALCULATED`, `REJECTED` ou `APPROVED`, isoladamente, não reservam o
  caminhão.
- A reserva operacional começa quando é criado o primeiro artefato operacional:
  uma sessão de carregamento ou uma viagem.
- Uma sessão de carregamento `PENDING` ou `IN_PROGRESS` mantém o caminhão
  ocupado.
- Uma sessão de carregamento `FINISHED` não libera o caminhão sozinha, pois a
  carga ainda pertence à operação até a conclusão da viagem.
- Uma viagem `SCHEDULED` ou `IN_ROUTE` mantém o caminhão ocupado.
- A reserva termina quando a viagem associada ao plano entra em `FINISHED`.
- Se o carregamento terminar e a viagem ainda não tiver sido criada, o caminhão
  continua reservado.
- Planos históricos `APPROVED` sem operação ativa não bloqueiam o caminhão.
- Artefatos pertencentes ao mesmo `load_plan_id` fazem parte da mesma operação
  e não entram em conflito entre si.
- O conflito ocorre somente entre operações de `load_plan_id` diferentes que
  utilizam o mesmo caminhão.
- A regra deve ficar centralizada no backend e ser reutilizável pelos módulos
  de planejamento, carregamento e viagens.
- O código público do conflito será `TRUCK_OPERATION_CONFLICT`.
- A mesma regra deverá ser reutilizável pela futura consulta de disponibilidade
  da OC67.

## Regra de disponibilidade

Um caminhão está ocupado quando existe outra operação utilizando o mesmo
`truck_id` e pelo menos uma das condições abaixo é verdadeira:

- existe sessão de carregamento e a viagem da operação ainda não está
  `FINISHED`;
- existe viagem em `SCHEDULED`;
- existe viagem em `IN_ROUTE`.

Um caminhão está disponível quando nenhuma outra operação ativa satisfaz essas
condições.

## Concorrência

A reserva deve ser protegida por transação.

Antes de verificar disponibilidade e criar o artefato operacional, a linha do
caminhão deve ser bloqueada para atualização.

Duas tentativas concorrentes de reservar o mesmo caminhão devem resultar em
apenas uma operação bem-sucedida.

A segunda tentativa deve falhar com `TRUCK_OPERATION_CONFLICT`, sem deixar
estado parcial persistido.

## Erro público

Código:

`TRUCK_OPERATION_CONFLICT`

O erro representa a tentativa de utilizar um caminhão que já está reservado
por outra operação ativa.

## Consequências

- Simulações e cálculos de planejamento continuam podendo usar o mesmo caminhão.
- Planos aprovados históricos não bloqueiam disponibilidade.
- O carregamento inicia a reserva operacional quando criado antes da viagem.
- O caminhão permanece reservado entre o fim do carregamento e a criação ou
  conclusão da viagem.
- A viagem concluída libera o caminhão.
- A OC67 poderá consultar disponibilidade sem duplicar regra de negócio.
- A OC65 poderá aplicar abordagem equivalente para conflito de motoristas.
