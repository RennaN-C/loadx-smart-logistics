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
- Enquanto não existir vínculo aprovado entre `users` e `drivers`, `DRIVER` acessa somente `/auth/me` na API atual.
- Papel e estado `active` são carregados do banco em cada requisição protegida; o papel gravado no JWT não é fonte única de autorização.

## Autenticação

- Usuário deve autenticar com e-mail e senha.
- Senha deve ser persistida somente como hash.
- Respostas públicas de usuário nunca devem retornar `password_hash`.
- Token JWT deve identificar o usuário pelo UUID em `sub`.
- Usuário inativo não pode fazer login.
- Somente `GET /health` e `POST /api/v1/auth/login` são públicos.
- Todos os demais endpoints de negócio exigem autenticação Bearer, salvo integração externa futura com autenticação própria aprovada.
- O primeiro `ADMIN` é criado por comando administrativo local, executado antes da exposição da API e somente quando não existem usuários.
- Depois do bootstrap, somente `ADMIN` cria usuários por `POST /api/v1/users`.
- `POST /api/v1/auth/register` não faz parte do contrato aprovado e deve ser removido na `OC51`.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado.

`SUPOSIÇÃO TÉCNICA`: o backend usa `pbkdf2_sha256` via Passlib para hash de senha nesta etapa, evitando incompatibilidade local do bcrypt no ambiente Python usado para testes.

`PENDENTE DE DEFINIÇÃO`: política final de expiração, refresh token, bloqueio por tentativas inválidas, força mínima e recuperação de senha permanece em `D18`.

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
- Produto não empilhável não pode receber outro volume por cima.
- Produto frágil não pode receber volume pesado por cima.

`PENDENTE DE DEFINIÇÃO`: limite objetivo para considerar um volume "pesado" sobre item frágil.

## Pedido

- Pedido deve possuir cliente e pelo menos um item.
- Quantidade de item deve ser maior que zero.
- Pedido cancelado não pode entrar em plano novo.
- `CONFIRMADO`: `delivery_sequence` é um inteiro positivo; valores maiores representam entregas posteriores e influenciam a ordem de carregamento.

Estados recomendados:

- `DRAFT`: pedido em criação.
- `READY`: pedido pronto para planejamento.
- `PLANNED`: pedido associado a plano calculado ou aprovado.
- `IN_TRANSIT`: pedido em viagem.
- `DELIVERED`: pedido entregue.
- `CANCELED`: pedido cancelado.

`RECOMENDAÇÃO`: estados devem ser armazenados em inglês e apresentados em português no frontend.

## Plano de carga

- Nenhum item pode ultrapassar os limites internos do baú.
- Dois itens não podem ocupar o mesmo espaço.
- Peso total colocado não pode superar o peso máximo do caminhão.
- Item sem posição deve ser registrado como não carregado.
- O mesmo volume individual não pode aparecer duas vezes no mesmo plano.
- Resultado deve registrar a versão do algoritmo.
- Somente plano calculado pode ser aprovado.
- Plano aprovado não deve ser alterado sem gerar nova versão ou recálculo.

Estados recomendados:

- `CALCULATING`.
- `CALCULATED`.
- `APPROVED`.
- `REJECTED`.
- `RECALCULATED`.

`PENDENTE DE DEFINIÇÃO`: política de versionamento quando um plano aprovado for recalculado.

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
- `CONFIRMADO`: não haverá tabela separada `volumes`; cada unidade será persistida futuramente em `load_plan_items` quando a camada de planejamento for integrada.

## Geometria incremental

- `CONFIRMADO`: a validação pura de limites usa coordenadas não negativas e `x + width <= truck_width`, `y + height <= truck_height`, `z + length <= truck_length`.
- `CONFIRMADO`: a classificação geométrica atual distingue separação, contato sem volume e interseção com volume positivo.
- `CONFIRMADO`: dimensões e coordenadas geométricas usam inteiros em centímetros, conforme a `ADR-008` e o contrato de persistência em `docs/03-modelo-dados.md`.
- `CONFIRMADO`: conforme a `ADR-009`, colisão exige sobreposição com extensão estritamente positiva nos três eixos; contato por face, aresta ou vértice é permitido.
- `CONFIRMADO`: a tolerância geométrica é zero e todas as comparações são exatas.

## Controle de peso incremental

- `CONFIRMADO`: o validador puro soma `current_weight_kg + candidate_weight_kg` usando `Decimal`.
- `CONFIRMADO`: peso exatamente igual ao máximo é aceito; excesso é rejeitado sem alterar o acumulado recebido.
- `PENDENTE DE DEFINIÇÃO`: definir o código público e a precedência da rejeição antes de integrar o peso à engine.

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

`RISCO IDENTIFICADO`: a posição retornada pela OC15 é somente um candidato provisório. Mesmo quando a política obrigatória usa o validador de colisão da OC16, ela não pode ser persistida nem enviada ao frontend antes das validações de apoio e empilhamento da OC17 e da revalidação física integrada.

### OC16 - colisão AABB

`CONFIRMADO`: conforme a `ADR-009`, duas caixas colidem somente quando a relação entre elas é `POSITIVE_OVERLAP`, com extensão estritamente positiva nos eixos `x`, `y` e `z`.

`CONFIRMADO`: `is_collision_free(candidate_box, placed_boxes)` aceita o candidato somente quando nenhuma caixa já posicionada possui sobreposição positiva com ele. Contato por face, aresta ou vértice é permitido e a tolerância geométrica é zero.

`CONFIRMADO`: a OC16 não implementa apoio, empilhamento, fragilidade, engine, persistência ou API e não cria um motivo público `COLLISION`. O catálogo de rejeições e sua precedência permanecem pendentes para a integração.

## Carregamento

- Carregamento só começa com plano aprovado.
- Checklist deve seguir `loading_sequence`.
- Alterar item do checklist não recalcula posição.
- Finalização do carregamento deve registrar horário.

Estados recomendados:

- `PENDING`.
- `IN_PROGRESS`.
- `CHECKED`.
- `FINISHED`.
- `CANCELED`.

## Viagem e entrega

- Viagem só começa com carregamento finalizado.
- Toda mudança de status gera histórico.
- Ocorrência não apaga o status anterior, apenas adiciona contexto.
- Entrega concluída deve registrar horário.

Estados de viagem recomendados:

- `SCHEDULED`.
- `IN_ROUTE`.
- `FINISHED`.
- `CANCELED`.

## Histórico de status

- Histórico deve registrar a entidade alterada, status anterior, novo status, usuário responsável quando houver e data/hora.
- `old_status` pode ser nulo quando for o primeiro status conhecido da entidade.
- `changed_by` é opcional para permitir registros automáticos do sistema.
- Quando `changed_by` for informado, deve apontar para um usuário existente.
- Histórico não deve ser removido ou sobrescrito por alterações de status futuras.

`PENDENTE DE DEFINIÇÃO`: lista final de entidades auditáveis e perfis autorizados a consultar histórico.

Estados de entrega recomendados:

- `PENDING`.
- `IN_DELIVERY`.
- `DELIVERED`.
- `DELAYED`.
- `CUSTOMER_ABSENT`.
- `FAILED`.
- `CANCELED`.

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

`PENDENTE DE DEFINIÇÃO`: mensagens de erro e confirmação enviadas ao motorista.

## IA

- Pode interpretar texto e explicar resultados.
- Não pode aprovar plano.
- Não pode ignorar validações determinísticas.
- Respostas estruturadas devem ser validadas antes de executar ações.
- Sistema deve continuar funcionando com provider mock.

## Relatórios

- Relatório de carregamento deve refletir caminhão, motorista, pedidos, produtos, volumes, peso, ocupação, rejeições e sequência de carregamento.
- Relatório de viagem deve refletir datas, motorista, caminhão, entregas, atrasos, ocorrências e status final.
- Relatório não pode recalcular plano de carga.

`PENDENTE DE DEFINIÇÃO`: layout final do PDF e campos obrigatórios para assinatura/conferência.
