# Planejamento de carga

Núcleo do sistema: expansão de volumes, rotações, pontos candidatos, colisões, peso, ocupação e persistência do plano.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `reference_service.py`: consulta pública e somente leitura usada por outros módulos.
- `router.py`: endpoints HTTP.
- `explanation.py`: contexto determinístico e neutro de provider para explicar um plano persistido.
- `optimizer/`: contratos e regras puras, sem banco ou HTTP.

Crie somente os arquivos necessários para a ocorrência atual.

## Estado incremental

- `CONFIRMADO`: OC11 calcula e valida a capacidade do caminhão no núcleo puro.
- `CONFIRMADO`: OC12 calcula o volume individual, expande quantidades com `volume_index` iniciado em `1` e não cria tabela separada `volumes`.
- `CONFIRMADO`: OC13 ordena volumes por uma chave total determinística e independente da ordem de entrada.
- `CONFIRMADO`: OC14 gera rotações ortogonais permitidas, com códigos priorizados e simetrias deduplicadas.
- `CONFIRMADO`: OC15 gera pontos candidatos estáveis e seleciona por first-fit uma posição provisória, com limites validados antes de uma política física obrigatória.
- `CONFIRMADO`: OC16 rejeita candidatos com sobreposição positiva nos três eixos em relação a qualquer caixa já posicionada, permite contato e usa tolerância zero.
- `CONFIRMADO`: OC17 exige apoio integral pela união exata de múltiplos suportes e valida empilhamento e fragilidade por toda a cadeia de carga.
- `CONFIRMADO`: OC18 controla o peso incremental com `Decimal`, formaliza os sete motivos públicos e seleciona o motivo final pela precedência fixa da `ADR-011`.
- `CONFIRMADO`: OC19 calcula volume usado, peso colocado, ocupação com duas casas, contagens e `heuristic-v1` conforme a `ADR-012`.
- `CONFIRMADO`: OC20 compõe OC11 a OC19 em `optimizer/engine.py`, aplica a
  profundidade em relação à porta, gera `loading_sequence` topológica e revalida
  todos os invariantes antes de publicar o resultado.
- `CONFIRMADO`: `load_plans`, `load_plan_orders` e `load_plan_items` persistem
  métricas, posições, rejeições e snapshots históricos, sem tabela `volumes`.
- `CONFIRMADO`: criação, detalhe, visualização, aprovação e recálculo estão
  disponíveis em `/api/v1/load-plans` com o RBAC da ADR-014.
- `CONFIRMADO`: a execução é síncrona e aceita no máximo 200 volumes expandidos.
- `CONFIRMADO`: pesos e ocupação permanecem `Decimal` no domínio e na
  persistência, mas são publicados como número JSON conforme D06 e ADR-016.

`RISCO IDENTIFICADO`: planos aprovados recalculados permanecem históricos e
imutáveis. Uma integração operacional futura deve escolher o descendente ativo
sem reescrever os anteriores.

## OC21 - comparação entre caminhões

`CONFIRMADO`: `POST /api/v1/load-plans/compare-trucks` recebe um ou mais
`order_ids` distintos e de 2 a 10 `truck_ids` distintos. Somente
`LOGISTICS_MANAGER` executa. O service conclui o preflight de todas as fontes e do
limite de 200 volumes antes de chamar a engine; qualquer pedido, produto ou
caminhão inexistente ou inválido falha a requisição inteira.

Cada candidato recebe a mesma carga materializada e é calculado integralmente por
`heuristic-v1`, sem copiar nem substituir regras de rotação, posicionamento,
colisão, apoio, peso, profundidade, rejeição, sequência ou métricas. Caminhão
válido que não comporte toda a carga retorna normalmente com `loaded_count`,
`unloaded_count`, `rejection_counts`, ocupação e peso.

A resposta `200` é um array direto na ordem de `truck_ids`. Essa ordem não é
ranking. A operação não persiste, não cria `LoadPlan`, não altera pedidos e não
retorna score, vencedor ou recomendação automática. Estado da OC21: concluída.

## OC22 - explicação do plano

`CONFIRMADO`: `POST /api/v1/load-plans/{id}/explain` explica somente um plano
persistido e tecnicamente válido. O builder recebe o agregado de `LoadPlan` com
`orders` e `items` já carregados; `LoadPlanRepository.get` garante esse formato
com `selectinload`. O service não chama a engine e não modifica o agregado.

`LoadPlanExplanationService` envia ao `AIProvider` somente métricas, snapshot do
caminhão, posições, rotações, sequência, rejeições, motivos e
`algorithm_version`. Nome, documento, telefone e endereço de cliente e dados
pessoais de motorista ficam fora do contexto.

Uma saída válida retorna `source = AI`. Timeout, indisponibilidade ou resposta
inválida retornam `source = FALLBACK` e texto determinístico; o timeout é
configurável e vale 5 segundos por padrão. Fallback não mascara `401`, `403`,
`404` nem `LOAD_PLAN_EXPLANATION_INVALID_PLAN`.

`CONFIRMADO`: a saída do provider tem teto de `MAX_EXPLANATION_LENGTH` (8.000
caracteres). Vazio já era recusado; sem teto superior, um adapter defeituoso ou
um modelo em laço devolveria megabytes e a aplicação aceitaria, e esse texto
atravessa a API até o navegador. Passar do limite é saída inválida como
qualquer outra e cai no `FALLBACK`, sem tocar o plano e sem persistir nada. O
limite é inclusivo: 8.000 é aceito, 8.001 não.

### RBAC da OC22, por perfil

A frase "aplica RBAC para LOGISTICS_MANAGER, ADMIN, CHECKER e DRIVER" pode ser
lida como se `DRIVER` tivesse permissão. Não tem. Por perfil, sem ambiguidade:

| Perfil | Acesso a `POST /load-plans/{id}/explain` |
|---|---|
| `ADMIN` | permitido, qualquer plano tecnicamente válido |
| `LOGISTICS_MANAGER` | permitido, qualquer plano tecnicamente válido |
| `CHECKER` | permitido **somente** para plano `APPROVED` |
| `DRIVER` | **proibido** |

### Provider fake e adapter externo

O que existe nesta entrega é a PORT mais um provider fake, e é isso que permite
executar e testar sem rede. O adapter externo concreto — SDK, credenciais,
comunicação real e prompt final — **não** faz parte dela e pertence ao
Desenvolvedor 4.

O caminho é `LoadPlan` -> `LoadPlanExplanationService` -> `AIProvider` ->
provider injetável -> validação da saída -> `AI` ou `FALLBACK`. Em nenhum ponto
a IA recalcula, aprova ou altera o plano.

Estado da OC22: concluída.

## OC87 — base multi-caminhão

`CONFIRMADO`: [contrato de distribuição](distributions.md), necessidade completa,
aprovação por partes, claims de identidade e API para OC88/OC89/OC90.
O caminho de um caminhão e a engine física permanecem compatíveis.

## OC88 — otimização automática multi-caminhão

`CONFIRMADO`: `optimizer/multi_truck.py` seleciona e particiona a frota
elegível sem banco ou HTTP. A busca é feita por quantidade crescente de
caminhões e cada avaliação delega o packing físico para
`calculate_volume_load_plan`.

`CONFIRMADO`: `POST /api/v1/load-distributions/optimize` executa preflight,
otimização e, somente quando existe cobertura completa, persiste a proposta
pelo `LoadDistributionService.create` da OC87.

`CONFIRMADO`: caminhões inativos, ocupados, em manutenção ou documentalmente
inelegíveis ficam fora da busca. Falta de capacidade retorna
`DISTRIBUTION_CAPACITY_INSUFFICIENT` sem distribuição parcial.

## Recuperação de planejamentos — #208

`CONFIRMADO`: GET /load-plans utiliza PageResponse, filtros status/truck_id e
ordenação created_at/id. Repository projeta somente colunas necessárias e
contagem de pedidos, sem carregar volumes. Service aplica o recorte APPROVED
para CHECKER antes da paginação; router mantém a autorização de leitura atual.
GET /{id}/continuity consulta interfaces públicas de carregamento/entrega e
compatibilidade operacional, sem escrita ou exposição de viagem ao conferente.
Contratos detalhados em docs/05-contratos-api.md. Sem alteração de schema,
engine, snapshots, aprovação, histórico ou estados. Head permanece 20261009_0023.


## OC90 — fluxo multi-caminhão

`CONFIRMADO`: A OC90 libera planos atuais de partes/distribuições APPROVED sem limite de uma
parte. Planos históricos permanecem bloqueados. A fronteira imutável pública
projeta pedidos, identidades e partes necessárias por pedido; consumidores não
importam tabelas privadas. Ver distributions.md e ADR-044 (proposta).


## Situação logística na recuperação — #255

`CONFIRMADO`: `GET /load-plans` aceita `operation_scope=all|ongoing|completed`
(padrão `all`, compatível) antes da paginação e com ordenação estável por data/ID.
O campo adicional `operation` contém IDs/estados de carregamento/viagem e contagens
agregadas de pedidos e entregas, sem carregar volumes. Projeções SQL passam pelos
serviços públicos dos módulos donos; a listagem mantém duas consultas.

O resumo e filtros operacionais exigem simultaneamente as permissões efetivas
`loadx.trips.read`, `loadx.orders.read` e `loadx.loading.read`. Sem elas o resumo
é nulo e filtros restritos retornam 403. O recorte APPROVED do CHECKER permanece.
Não há acesso novo a dados pessoais de motoristas ou notificações.

`CONFIRMADO`: aprovação do plano não significa conclusão logística. `COMPLETED`
é projeção de viagem FINISHED **e** todos os pedidos relacionados DELIVERED
(globalmente, incluindo as partes obrigatórias). Uma parte entregue com pedido
IN_TRANSIT é parcial; viagem CANCELED não é concluída nem em andamento. Planos
sem operação continuam NOT_STARTED, inclusive cálculos históricos. `ongoing`
inclui preparações não rejeitadas e operações ativas/parciais; `all` inclui também
rejeitados/cancelados. Nenhum estado, snapshot ou histórico persistido é alterado.

`GET /{id}/continuity` retorna os cinco estados OC94 da viagem e o mesmo resumo
autorizado. `orders_ready_for_approval` no detalhe é um booleano atual do servidor
para evitar oferecer aprovação/recálculo de cálculo cujos pedidos já saíram de
READY. É orientação de UI; locks e validações da aprovação continuam sendo a
fonte de verdade, inclusive se os dados mudarem após a consulta.

Sem migration: head confirmado `20261021_0034`. O head antigo mencionado na seção
histórica da #208 não descreve o schema atual.
