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

`LOGISTICS_MANAGER` e `ADMIN` explicam qualquer plano persistido tecnicamente
válido; `CHECKER` somente plano `APPROVED`; `DRIVER` não acessa. A port e o
provider fake permitem execução e testes sem rede. Adapter externo, SDK,
credenciais e comunicação real pertencem ao Desenvolvedor 4. Estado da OC22:
concluída.
