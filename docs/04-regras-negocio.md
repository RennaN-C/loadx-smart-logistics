# Regras de negócio

## Unidades

- `CONFIRMADO`: dimensões em centímetros.
- `CONFIRMADO`: peso em quilogramas.
- `CONFIRMADO`: porcentagem de 0 a 100.
- `CONFIRMADO`: horários armazenados em UTC.
- `CONFIRMADO`: coordenadas usam `x = largura`, `y = altura`, `z = comprimento`.
- `CONFIRMADO`: a origem `(0, 0, 0)` fica no piso, no canto frontal esquerdo do baú.

## Perfis

`CONFIRMADO`: perfis previstos no documento-base:

- `ADMIN`: administrador.
- `CHECKER`: conferente.
- `DRIVER`: motorista.
- `LOGISTICS_MANAGER`: responsável logístico.

`RECOMENDAÇÃO`: usar estes nomes em inglês no código e mapear para textos em português na interface.

`CONFIRMADO`: a autorização segue menor privilégio e negação por padrão, conforme `ADR-004`. Acesso não listado é negado.

Legenda:

- `G`: gerenciar, incluindo criar, consultar, atualizar e executar as ações permitidas do recurso.
- `R`: consultar.
- `S`: acessar apenas registros vinculados ao usuário autenticado.
- `-`: acesso negado.

| Recurso | `ADMIN` | `LOGISTICS_MANAGER` | `CHECKER` | `DRIVER` |
|---|---|---|---|---|
| Usuários | G | Próprio em `/auth/me` | Próprio em `/auth/me` | Próprio em `/auth/me` |
| Clientes | R | G | - | - |
| Motoristas | R | G | - | - |
| Caminhões | R | G | R | S futuro |
| Produtos | R | G | R | S futuro |
| Pedidos | R | G | R | S futuro |
| Planos de carga | R | G, calcular e aprovar | S em plano aprovado | S em instruções atribuídas |
| Carregamento | R | G e supervisionar | S em checklist atribuído | S para consulta |
| Viagens | R | G e atribuir | - | S em transições permitidas |
| Entregas | R | G e tratar exceções | - | S em transições permitidas |
| Ocorrências | R | G, classificar e resolver | S em carregamento | S em viagem ou entrega |
| Histórico geral | R | R | - | - |
| Relatórios | R e gerar | R e gerar | S de carregamento | S da própria viagem |

Regras complementares:

- `ADMIN` administra identidades e consulta a operação; alterações operacionais pertencem ao `LOGISTICS_MANAGER`.
- `CHECKER` pode consultar caminhões, produtos e pedidos necessários à conferência, sem acessar cadastros pessoais de clientes ou motoristas.
- Permissão de consulta não libera automaticamente todos os campos pessoais; seleção, omissão e mascaramento de campos seguem `D12`.
- Acesso `S` exige vínculo comprovado no banco e validação do objeto solicitado, não apenas do perfil.
- `DRIVER` sem `users.driver_id` acessa somente `/auth/me`; o vínculo é único,
  administrado por `ADMIN` e exige papel `DRIVER`.
- Em viagens e entregas, `DRIVER` precisa estar ativo, apontar para motorista
  ativo e somente pode consultar ou operar objetos com o mesmo `driver_id`.
- Papel e estado `active` são carregados do banco em cada requisição protegida.

## Autenticação

- Usuário deve autenticar com e-mail e senha.
- Senha deve ser persistida somente como hash.
- Respostas públicas de usuário nunca devem retornar `password_hash`.
- A sessão opaca deve vincular o usuário pelo UUID e persistir somente o hash do
  identificador aleatório.
- Usuário inativo não pode fazer login.
- Somente `GET /health`, `GET /ready` e `POST /api/v1/auth/login` são públicos.
- `/health` mede apenas liveness. `/ready` exige PostgreSQL acessível e revisão
  Alembic exatamente no head, conforme D11 e `ADR-018`.
- Todos os demais endpoints de negócio exigem o cookie de sessão do frontend
  próprio, salvo integração externa futura com autenticação própria aprovada.
- O primeiro `ADMIN` é criado por comando administrativo local, executado antes da exposição da API e somente quando não existem usuários.
- Depois do bootstrap, somente `ADMIN` cria usuários por `POST /api/v1/users`.
- `POST /api/v1/auth/register` não faz parte do contrato aprovado e deve ser removido na `OC51`.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado.

`CONFIRMADO` por D18 e `ADR-020`:

- não existe refresh token no MVP;
- sessões expiram após 30 minutos de inatividade ou 8 horas absolutas;
- produção usa cookie `__Host-loadx_session` com `HttpOnly`, `Secure`,
  `SameSite=Lax`, `Path=/` e sem `Domain`;
- métodos inseguros validam `Origin` exata e sessões autenticadas também exigem
  `X-CSRF-Token` associado à sessão;
- logout, troca de senha, desativação e alteração de papel revogam sessões;
- login é limitado por conta e IP, com bloqueios de 1, 5, 15 e 60 minutos a
  partir da quinta falha;
- credenciais inválidas, conta inexistente e conta inativa produzem a mesma
  resposta pública;
- novas senhas exigem 15 a 128 caracteres, permitem espaços e Unicode, não
  exigem composição nem troca periódica e consultam a blocklist interna mais um
  arquivo UTF-8 opcional configurado pela operação;
- novos hashes usam Argon2id com m=19 MiB, t=2 e p=1; PBKDF2 legado é migrado
  após login válido.

`PENDENTE DE DEFINIÇÃO`: recuperação de senha e MFA para funções críticas serão
tratados em ocorrências próprias.

## Caminhão

- Placa deve ser única.
- Dimensões internas devem ser maiores que zero.
- Peso máximo deve ser maior que zero.
- Caminhão inativo não pode receber novo plano.
- Caminhão usado em plano aprovado não deve ser removido fisicamente.

`RECOMENDAÇÃO`: usar `active = false` para indisponibilidade operacional em vez de exclusão física.

## Motorista

- Nome, documento, telefone e CNH devem ser informados para cadastro completo.
- Motorista inativo não pode ser vinculado a nova viagem.
- Telefone é necessário para comandos por WhatsApp simulado/controlado.
- `users.driver_id` é opcional e único; vínculo não nulo exige usuário com papel
  `DRIVER`.
- Alterar ou remover o vínculo revoga todas as sessões do usuário na mesma
  transação.

`PENDENTE DE DEFINIÇÃO`: validação formal de CPF, telefone e categoria de CNH.

## Cliente

- Pedido deve estar vinculado a um cliente.
- Documento do cliente deve ser armazenado como texto.
- Dados pessoais reais não podem ser usados em seeds ou testes.

`PENDENTE DE DEFINIÇÃO`: regra final de unicidade para CPF/CNPJ em clientes.

## Produto

- Dimensões e peso devem ser maiores que zero.
- Quantidade pertence ao item do pedido, não ao cadastro do produto.
- Produto com rotação bloqueada mantém sua orientação original.
- `CONFIRMADO`: produto não empilhável pode ser colocado no topo, mas não pode atuar como suporte direto de outro volume.
- `CONFIRMADO`: produto frágil pode ser colocado no topo, mas não pode receber carga positiva como suporte direto ou ancestral.
- `CONFIRMADO`: não existe limite de volume "pesado"; qualquer carga transmitida possui peso positivo e aciona a regra de fragilidade.

## Pedido

- Pedido deve possuir cliente e pelo menos um item.
- Quantidade de item deve ser maior que zero.
- Pedido cancelado não pode entrar em plano novo.
- `CONFIRMADO`: `delivery_sequence` é um inteiro positivo; valores maiores representam entregas posteriores e influenciam a ordem de carregamento.
- `CONFIRMADO` por `ADR-022`: todos os itens do mesmo pedido usam a mesma
  `delivery_sequence`. Na viagem, pedidos são ordenados por essa sequência e
  UUID e recebem entregas contíguas a partir de `1`.
- `CONFIRMADO`: somente pedidos `READY` entram na criação comum de plano; eles
  passam a `PLANNED` apenas na aprovação.
- `CONFIRMADO`: o conjunto de itens não pode ser substituído depois que algum
  `order_item` for referenciado por `load_plan_items`.

Estados recomendados:

- `DRAFT`: pedido em criação.
- `READY`: pedido pronto para planejamento.
- `PLANNED`: pedido associado a plano aprovado.
- `IN_TRANSIT`: pedido em viagem.
- `DELIVERED`: pedido entregue.
- `CANCELED`: pedido cancelado.

`RECOMENDAÇÃO`: estados devem ser armazenados em inglês e apresentados em português no frontend.

`CONFIRMADO` por D04 e ADR-015: as transições manuais do
`LOGISTICS_MANAGER` são:

- `DRAFT -> READY` ou `DRAFT -> CANCELED`;
- `READY -> DRAFT` ou `READY -> CANCELED`.

`CONFIRMADO`: `READY -> PLANNED` pertence somente à aprovação de plano;
`PLANNED -> IN_TRANSIT` pertence ao início válido da viagem; e
`IN_TRANSIT -> DELIVERED` pertence à conclusão válida da entrega. `DELIVERED` e
`CANCELED` são terminais. D08 mantém cancelamento, falha, ausência e atraso fora
da OC09 até ocorrer uma nova decisão com migration própria.

`CONFIRMADO`: somente `DRAFT` aceita edição de cliente, prioridade, endereço,
previsão e itens. `READY` deve voltar a `DRAFT` antes de qualquer edição;
`PLANNED`, `IN_TRANSIT`, `DELIVERED` e `CANCELED` são imutáveis. Itens já
referenciados por plano permanecem imutáveis mesmo em `DRAFT`.

`CONFIRMADO`: a prioridade do pedido aceita somente `LOW`, `NORMAL`, `HIGH` e
`URGENT`. A entrada é normalizada para maiúsculas antes da validação.

`CONFIRMADO`: repetir o estado atual é idempotente e não cria histórico. Status
não é alterado pelo `PATCH` genérico de pedido.

## Plano de carga

- Nenhum item pode ultrapassar os limites internos do baú.
- Dois itens não podem ocupar o mesmo espaço.
- Peso total colocado não pode superar o peso máximo do caminhão.
- Item sem posição deve ser registrado como não carregado.
- O mesmo volume individual não pode aparecer duas vezes no mesmo plano.
- Resultado deve registrar a versão do algoritmo.
- Somente plano `CALCULATED` sem rejeições pode ser aprovado.
- Plano aprovado não deve ser alterado sem gerar nova versão ou recálculo.

Estados persistidos:

- `CALCULATED`.
- `APPROVED`.
- `REJECTED`.

`CONFIRMADO`: plano parcial permanece `CALCULATED` para inspeção, mas não pode ser
aprovado. `SUPOSIÇÃO TÉCNICA`: quando nenhum volume é colocado, o plano é
`REJECTED`.

`CONFIRMADO`: recálculo sempre cria novo plano com `recalculated_from_id`, usa os
dados atuais e novos snapshots e não altera a origem. Para conciliar a origem
aprovada com o estado do pedido, o recálculo herdado aceita seus pedidos exatos
em `READY` ou `PLANNED`; a criação comum continua aceitando somente `READY`.

## Capacidade do caminhão

- Capacidade volumétrica interna é calculada por `internal_width_cm * internal_height_cm * internal_length_cm`.
- O resultado volumétrico inicial é registrado em `internal_volume_cm3`.
- Dimensões internas e peso máximo devem ser maiores que zero antes do cálculo.
- O cálculo de capacidade não acessa banco, HTTP ou IA.

## Volume individual e expansão

- `CONFIRMADO`: o núcleo puro calcula o volume individual em centímetros cúbicos por `width_cm * height_cm * length_cm`.
- `CONFIRMADO`: a expansão em memória materializa exatamente `quantity` unidades e usa a composição `order_item_id` mais `volume_index` como identidade individual.
- `CONFIRMADO`: dimensões, quantidade e sequência devem ser inteiros positivos; peso deve ser `Decimal` positivo e finito.
- `CONFIRMADO`: coleções não ordenadas e `order_item_id` duplicados são rejeitados para preservar identidade e reprodução.
- `CONFIRMADO`: conforme `ADR-005`, `volume_index` começa em `1` para cada item e a identidade individual é `(order_item_id, volume_index)`.
- `CONFIRMADO`: não existe tabela separada `volumes`; cada unidade é persistida em `load_plan_items` pela camada de planejamento.

## Geometria incremental

- `CONFIRMADO`: a validação pura de limites usa coordenadas não negativas e `x + width <= truck_width`, `y + height <= truck_height`, `z + length <= truck_length`.
- `CONFIRMADO`: a classificação geométrica atual distingue separação, contato sem volume e interseção com volume positivo.
- `CONFIRMADO`: dimensões e coordenadas geométricas usam inteiros em centímetros, conforme a `ADR-008` e o contrato de persistência em `docs/03-modelo-dados.md`.
- `CONFIRMADO`: conforme a `ADR-009`, colisão exige sobreposição com extensão estritamente positiva nos três eixos; contato por face, aresta ou vértice é permitido.
- `CONFIRMADO`: a tolerância geométrica é zero e todas as comparações são exatas.

## Controle de peso incremental

- `CONFIRMADO`: o validador puro soma `current_weight_kg + candidate_weight_kg` usando `Decimal`.
- `CONFIRMADO`: peso exatamente igual ao máximo é aceito; excesso é rejeitado sem alterar o acumulado recebido.
- `CONFIRMADO`: excesso usa `TRUCK_WEIGHT_EXCEEDED`. O acumulado da orquestração só pode ser substituído pelo total retornado em uma tentativa aceita, de modo que apenas volumes colocados componham o peso total.
- `CONFIRMADO`: conforme a `ADR-011`, a precedência pública é `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`, `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`, `INSUFFICIENT_SUPPORT`, `COLLISION` e `NO_VALID_POSITION`. Entrada inválida é erro de domínio/API, não rejeição de volume.

## Aproveitamento e métricas

- `CONFIRMADO`: conforme a `ADR-012`, `used_volume_cm3` soma somente o volume físico dos itens colocados. Rejeitados não contribuem para volume usado nem peso total.
- `CONFIRMADO`: `occupancy_percent = used_volume_cm3 / internal_volume_cm3 * 100`, usando `Decimal`, duas casas e `ROUND_HALF_UP`. O arredondamento ocorre uma única vez, depois da soma completa.
- `CONFIRMADO`: carga sem colocados retorna `0.00`, ocupação integral retorna `100.00` e um total colocado acima do volume interno é erro de domínio, não percentual limitado silenciosamente.
- `CONFIRMADO`: `loaded_count` e `unloaded_count` contam as coleções disjuntas de colocados e rejeitados. A engine deve comprovar que elas formam uma partição completa da entrada.
- `CONFIRMADO`: a versão inicial é `heuristic-v1`; qualquer mudança de regra determinística que altere o resultado exige nova `algorithm_version`.

## Otimizador

- A IA generativa não posiciona volumes.
- O otimizador deve ser determinístico, testável e reproduzível.
- O mesmo input deve produzir o mesmo output para a mesma `algorithm_version`.
- Uma solução inválida nunca pode ser aceita para melhorar a porcentagem de ocupação.
- Limites, colisão, rotação, peso, apoio e empilhamento devem ser validados por código.
- O otimizador não acessa banco, HTTP, FastAPI, WhatsApp ou provedor de IA.

`CONFIRMADO`: conforme `ADR-006`, a prioridade de tentativa usa a chave total:

1. maior `volume_cm3`;
2. maior `weight_kg`;
3. não empilhável antes de empilhável;
4. não frágil antes de frágil;
5. maior `delivery_sequence`, que representa entrega posterior;
6. menor valor inteiro não assinado do UUID de `order_item_id`;
7. menor `volume_index`.

`CONFIRMADO`: entradas com as mesmas identidades e atributos produzem a mesma ordem, independentemente da ordem em que foram recebidas. Identidades duplicadas são rejeitadas.

`CONFIRMADO`: a prioridade de tentativa não define sozinha a profundidade no caminhão nem a `loading_sequence`; essas regras pertencem ao posicionamento e ao carregamento.

### OC14 - rotações permitidas

`CONFIRMADO`: conforme `ADR-007`, os códigos seguem a prioridade `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY`, `ZYX`. Cada letra indica qual eixo original ocupa, respectivamente, os eixos usados `x`, `y` e `z`.

`CONFIRMADO`: `X`, `Y` e `Z` originais representam `width`, `height` e `length`. As dimensões usadas acompanham a permutação registrada no código.

`CONFIRMADO`: produto com `rotation_allowed = false` gera somente `XYZ`. Orientações geometricamente iguais são deduplicadas, preservando o primeiro código da ordem oficial.

### OC15 - posicionamento first-fit

`CONFIRMADO`: conforme a `ADR-008`, os pontos candidatos incluem a origem `(0, 0, 0)` e as origens das faces positivas de cada caixa já posicionada. Para uma caixa em `(x, y, z)` com dimensões usadas `(w, h, l)`, os novos pontos são `(x + w, y, z)`, `(x, y + h, z)` e `(x, y, z + l)`.

`CONFIRMADO`: pontos idênticos são deduplicados e as combinações de ponto e rotação são avaliadas pela chave total `(y, z, x, rotation_rank)`, com a prioridade de rotação definida na `ADR-007`.

`CONFIRMADO`: o posicionamento usa first-fit. Cada candidato deve caber integralmente nos limites internos antes de ser submetido a uma política física obrigatória fornecida pelo chamador; não existe política permissiva padrão.

`CONFIRMADO`: `TRUCK_DIMENSIONS_EXCEEDED` identifica o volume para o qual nenhuma rotação permitida cabe nas dimensões internas nem na origem. `NO_VALID_POSITION` é o fallback quando existe uma rotação dimensionalmente viável, mas nenhuma combinação é aceita e nenhuma regra física mais específica produz outro motivo.

`CONFIRMADO`: o candidato da OC15 só é publicado depois que a engine da OC20
compõe colisão, apoio, peso, profundidade, motivo final e revalidação física.

### OC16 - colisão AABB

`CONFIRMADO`: conforme a `ADR-009`, duas caixas colidem somente quando a relação entre elas é `POSITIVE_OVERLAP`, com extensão estritamente positiva nos eixos `x`, `y` e `z`.

`CONFIRMADO`: `is_collision_free(candidate_box, placed_boxes)` aceita o candidato somente quando nenhuma caixa já posicionada possui sobreposição positiva com ele. Contato por face, aresta ou vértice é permitido e a tolerância geométrica é zero.

`CONFIRMADO`: `COLLISION` integra o catálogo aprovado na OC18 e seu mapeamento
explicativo é realizado pela engine da OC20.

### OC17 - apoio, empilhamento e fragilidade

`CONFIRMADO`: conforme a `ADR-010`, um volume no piso, com `y = 0`, é integralmente apoiado. Acima do piso, um suporte direto exige coincidência exata entre seu topo e a base do volume apoiado, além de sobreposição com extensão positiva nos eixos `x` e `z`.

`CONFIRMADO`: a base deve ter 100% de apoio pela união geométrica exata dos retângulos de contato de um ou mais suportes diretos. Áreas sobrepostas são contadas uma única vez; não existe tolerância, arredondamento nem apoio parcial aceito.

`CONFIRMADO`: cada aresta de apoio transmite carga positiva por todos os ramos até todos os ancestrais. Todo suporte direto deve ser empilhável e nenhum suporte direto ou ancestral que receba carga pode ser frágil.

`CONFIRMADO`: as flags do próprio candidato não impedem sua colocação no topo. Um candidato frágil ou não empilhável pode ser aceito quando nenhum volume acima transmite carga para ele. Não existe limite de volume "pesado" para aplicar a regra de fragilidade.

`CONFIRMADO`: `SupportAssessment`, `analyze_support_configuration`, `is_support_configuration_valid` e `is_candidate_support_valid` formam a API pura da OC17.

`CONFIRMADO`: `NON_STACKABLE_SUPPORT`,
`FRAGILE_SUPPORT_WEIGHT_EXCEEDED` e `INSUFFICIENT_SUPPORT` integram o catálogo da
OC18 e são mapeados pela engine da OC20.

### OC20 - profundidade, engine e sequência

`CONFIRMADO`: a porta fica no plano `z = internal_length_cm`. A distância até a
porta usa a face do volume voltada a esse plano:
`internal_length_cm - (position_z_cm + used_length_cm)`.

`CONFIRMADO`: maior `delivery_sequence` exige distância até a porta maior ou
igual. Igualdade permite volumes lado a lado. Quando somente essa regra bloqueia
um candidato fisicamente válido, o motivo é `NO_VALID_POSITION`.

`CONFIRMADO`: a `loading_sequence` é 1-based, contígua e topológica. Suportes
diretos são carregados antes dos volumes apoiados; entre os disponíveis, a ordem
usa entrega decrescente, distância da porta decrescente e identidade estável.

`CONFIRMADO`: a execução é síncrona e aceita no máximo 200 volumes. A engine
revalida partição, limites, rotações, colisões, apoio, peso, profundidade,
sequência e métricas antes de retornar `heuristic-v1`.

## Carregamento

- `CONFIRMADO`: carregamento só pode ser criado para plano `APPROVED` com ao
  menos um volume posicionado, e existe no máximo uma sessão por plano.
- `CONFIRMADO`: sessão aceita apenas `PENDING -> IN_PROGRESS -> FINISHED`; item
  aceita apenas `PENDING -> CHECKED` durante `IN_PROGRESS`.
- `CONFIRMADO`: alterar item do checklist não recalcula posição.
- `CONFIRMADO`: `FINISHED` exige todos os itens `CHECKED` e registra
  `finished_at` em UTC.
- `CONFIRMADO`: somente a sessão `FINISHED` do mesmo plano libera o início da
  viagem; sessão ausente, incompleta ou pertencente a outro plano não libera.
- `CONFIRMADO`: `CHECKER` e `LOGISTICS_MANAGER` operam; `ADMIN` apenas consulta;
  `DRIVER` não acessa os endpoints de carregamento.

## Viagem e entrega

- `CONFIRMADO`: viagem nasce `SCHEDULED` a partir de plano `APPROVED`, motorista
  ativo e todos os pedidos do plano em `PLANNED`.
- `CONFIRMADO`: cada plano pertence a no máximo uma viagem e cada pedido a no
  máximo uma entrega no MVP.
- `CONFIRMADO`: viagem só começa quando a interface pública do carregamento
  confirmar sessão `FINISHED` para o mesmo plano; qualquer ausência ou
  divergência falha fechada e bloqueia `IN_ROUTE`.
- `CONFIRMADO`: iniciar a viagem executa `SCHEDULED -> IN_ROUTE`, registra
  `started_at` e move atomicamente todos os pedidos `PLANNED -> IN_TRANSIT`.
- `CONFIRMADO`: finalizar executa `IN_ROUTE -> FINISHED` e registra
  `finished_at` somente quando todas as entregas e pedidos estão `DELIVERED`.
- `CONFIRMADO`: entrega executa apenas `PENDING -> IN_DELIVERY -> DELIVERED`
  durante uma viagem `IN_ROUTE`; a conclusão registra `delivered_at` e move o
  pedido correspondente `IN_TRANSIT -> DELIVERED`.
- `CONFIRMADO`: repetir o status atual é idempotente e não cria histórico.
- `CONFIRMADO`: `LOGISTICS_MANAGER` cria e opera; `ADMIN` somente consulta;
  `DRIVER` consulta e opera apenas sua própria viagem; `CHECKER` não acessa.
- `CONFIRMADO`: viagem, entrega, pedidos e todos os registros de histórico da
  ação compartilham um único commit ou rollback.
- Ocorrência não apaga o status anterior, apenas adiciona contexto.

## Histórico de status

- Histórico deve registrar a entidade alterada, status anterior, novo status, usuário responsável quando houver e data/hora.
- `old_status` pode ser nulo quando for o primeiro status conhecido da entidade.
- `changed_by` é opcional para permitir registros automáticos do sistema.
- Quando `changed_by` for informado, deve apontar para um usuário existente.
- Histórico não deve ser removido ou sobrescrito por alterações de status futuras.

`CONFIRMADO` por D05 e ADR-015: o service dono bloqueia a entidade e controla um
único commit ou rollback para entidade e histórico. Operações compostas usam
`stage_status_change` e `flush`; ações manuais registram o usuário autenticado,
ações realmente automáticas podem usar `changed_by = null`, e a criação do
pedido registra `null -> DRAFT`.

`CONFIRMADO` por D10 e `ADR-022`: as entidades auditáveis aceitas são `ORDER`,
`LOAD_PLAN`, `TRIP` e `DELIVERY`. Não há endpoint público de histórico na OC09;
services internos continuam disponíveis aos módulos donos.

## Ocorrências

Tipos previstos no documento-base:

- `DAMAGED_PRODUCT`: produto avariado.
- `CUSTOMER_ABSENT`: cliente ausente.
- `WRONG_ADDRESS`: endereço incorreto.
- `REFUSED_PRODUCT`: produto recusado.
- `MISSING_VOLUME`: volume faltante.
- `DELAY`: atraso.
- `VEHICLE_PROBLEM`: problema no veículo.
- `LOADING_PROBLEM`: problema no carregamento.

Regras:

- Ocorrência deve ter tipo e descrição.
- Foto é opcional no MVP.
- Ocorrência deve estar vinculada a viagem e, quando aplicável, a entrega.
- Registro de ocorrência não deve excluir nem sobrescrever histórico.

## WhatsApp e mensagens

Comandos controlados previstos:

- `INICIAR VIAGEM`.
- `CHEGUEI`.
- `INICIAR ENTREGA`.
- `FINALIZAR ENTREGA`.
- `OCORRÊNCIA`.
- `STATUS`.
- `PRÓXIMA ENTREGA`.

Regras:

- Mensagem recebida deve ser associada a motorista conhecido.
- Interpretação de linguagem natural deve virar intenção estruturada.
- Intenção só executa ação se for permitida para o estado atual.
- Provider real ou mock deve seguir a mesma interface.

`CONFIRMADO`: o fluxo controlado responde confirmação explícita e somente marca
`executed = true` após o service público concluir a ação. Motorista desconhecido
ou inativo, usuário sem vínculo, viagem ambígua/ausente e estado inválido não
alteram dados.

## IA

- Pode interpretar texto e explicar resultados.
- Não pode aprovar plano.
- Não pode ignorar validações determinísticas.
- Respostas estruturadas devem ser validadas antes de executar ações.
- Sistema deve continuar funcionando com provider mock.

## Relatórios

- `CONFIRMADO`: relatório de carregamento reflete plano, caminhão, volumes,
  sequência, conferência, início, fim e status.
- `CONFIRMADO`: relatório de viagem reflete viagem, caminhão, entregas, status,
  ocorrências e datas.
- `CONFIRMADO`: relatório não recalcula nem altera plano de carga.

`PENDENTE DE DEFINIÇÃO`: layout final do PDF e campos obrigatórios para assinatura/conferência.
