# Fluxo operacional

## Fluxo ponta a ponta

```text
Cadastro de caminhão, cliente, motorista e produtos
          ↓
Criação do pedido com itens e sequência de entrega
          ↓
Seleção de caminhão e pedidos
          ↓
Geração do plano de carga
          ↓
Validações geométricas, peso, rotação, apoio e empilhamento
          ↓
Registro de volumes posicionados e rejeitados
          ↓
Aprovação do plano
          ↓
Visualização 3D e checklist
          ↓
Finalização do carregamento
          ↓
Criação e início da viagem
          ↓
Atualização das entregas
          ↓
Registro de ocorrências
          ↓
Conclusão e relatório
```

## Caminho crítico para a primeira demonstração

`CONFIRMADO`: o primeiro incremento integrado deve terminar na visualização 3D. O segundo deve terminar no relatório de entrega.

## Fluxo de planejamento de carga

1. Responsável logístico seleciona caminhão ativo.
2. Responsável logístico seleciona pedidos elegíveis.
3. Backend carrega dimensões, peso máximo, itens e regras físicas.
4. Service do módulo `load_planning` cria DTOs e snapshots imutáveis.
5. Otimizador expande e ordena volumes, testa rotações, gera pontos candidatos e valida cada posição.
6. Volumes válidos recebem posição, dimensões usadas, rotação e sequência topológica de carregamento.
7. Volumes inválidos recebem `rejection_reason`.
8. Otimizador calcula ocupação, peso, totais e `algorithm_version`; o service orquestra e prepara a persistência.
9. Repository persiste `load_plans`, `load_plan_orders` e `load_plan_items`.
10. API retorna resumo para o frontend.

`CONFIRMADO`: criação aceita somente caminhão ativo, pedidos `READY` e até 200
volumes. O cálculo é síncrono. Pedido permanece `READY` até a aprovação de um
plano completo.

`CONFIRMADO`: aprovação grava plano `APPROVED`, pedidos `PLANNED` e históricos em
um único commit. Recálculo cria outro plano com dados atuais e
`recalculated_from_id`, sem alterar a origem.

`CONFIRMADO`: o frontend não corrige nem recalcula posições.

## Fluxo de visualização 3D

1. Frontend solicita `GET /load-plans/{id}/visualization`.
2. API retorna dimensões internas do caminhão e itens posicionados.
3. Feature `load-visualization` renderiza baú e volumes com React Three Fiber.
4. Usuário pode girar a câmera 3D da cena, aproximar, selecionar volume e destacar categorias.
5. Informação exibida deve vir do contrato da API.

`RECOMENDAÇÃO`: conversões visuais de escala podem existir apenas na camada de renderização e não podem alterar valores persistidos em centímetros.

## Fluxo de carregamento

1. Conferente abre plano aprovado.
2. Sistema cria ou recupera `loading_session`.
3. Checklist segue `loading_sequence`.
4. Conferente marca volumes conferidos.
5. Ao finalizar, sistema registra horário e libera o início de uma viagem já
   criada para o plano aprovado.

`PENDENTE DE DEFINIÇÃO`: regra de bloqueio quando um item do checklist não for conferido.

## Fluxo de viagem e entrega

1. Responsável logístico seleciona plano `APPROVED` e motorista ativo.
2. Backend bloqueia plano, motorista e pedidos, cria a viagem `SCHEDULED`, gera
   uma entrega `PENDING` por pedido em ordem determinística e grava os históricos
   em uma transação.
3. Responsável logístico ou motorista vinculado solicita `IN_ROUTE`.
4. A interface pública de carregamento confirma `FINISHED`; sem essa confirmação
   o início falha fechado.
5. Backend registra `started_at`, move todos os pedidos `PLANNED -> IN_TRANSIT`
   e grava os históricos no mesmo commit.
6. Durante `IN_ROUTE`, o responsável ou motorista vinculado avança cada entrega
   por `PENDING -> IN_DELIVERY -> DELIVERED`.
7. A conclusão da entrega registra `delivered_at`, move seu pedido
   `IN_TRANSIT -> DELIVERED` e grava ambos os históricos atomicamente.
8. A viagem só executa `IN_ROUTE -> FINISHED` e registra `finished_at` quando
   todas as entregas e pedidos estão `DELIVERED`.
9. Ocorrências futuras poderão adicionar contexto sem apagar o histórico.

`CONFIRMADO`: o módulo de carregamento materializa `FINISHED` e libera somente a
viagem do mesmo plano. Estados de cancelamento, falha, ausência e atraso
continuam fora do ciclo persistido da v1.0.0.

## Fluxo de WhatsApp simulado/controlado

1. Provider recebe mensagem.
2. Adapter identifica motorista pelo telefone.
3. Serviço de mensagens interpreta comando controlado ou frase natural.
4. Intenção estruturada é validada por schema.
5. Service público executa a ação somente se o estado atual permitir.
6. Sistema registra histórico/auditoria.
7. Provider responde confirmação ou erro operacional.

`CONFIRMADO`: provider mock deve permitir desenvolver e testar sem serviço externo real.

## Fluxo de ocorrência

1. Usuário ou motorista informa tipo e descrição.
2. Sistema valida tipo permitido.
3. Foto opcional é associada por URL ou referência mock.
4. Ocorrência é vinculada à viagem e, quando aplicável, à entrega.
5. Histórico de status permanece preservado.
6. Relatórios passam a incluir a ocorrência.

## Fluxo de relatório

1. Usuário solicita relatório de plano ou viagem.
2. Backend busca dados persistidos.
3. Serviço de relatórios monta PDF simples.
4. API retorna download ou referência do arquivo.

`CONFIRMADO`: na v1.0.0 o PDF é gerado em memória e retornado como download;
armazenamento permanente e envio por e-mail/WhatsApp ficam fora do escopo.
