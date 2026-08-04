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
- `delivery_sequence` orienta descarga e influencia a ordem de carregamento.

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
- `SUPOSIÇÃO TÉCNICA`: as primitivas atuais usam inteiros em centímetros, de acordo com os models existentes; a precisão persistida continua pendente.
- `PENDENTE DE DEFINIÇÃO`: decidir se contato de face, aresta ou vértice é colisão e definir eventual tolerância antes de criar o validador final.

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

Critérios de ordenação previstos:

- Maior volume primeiro.
- Maior peso primeiro.
- Produtos não empilháveis primeiro.
- Produtos frágeis por último quando houver empilhamento.
- Produtos da última entrega mais ao fundo.
- Produtos da primeira entrega próximos da porta.

`RECOMENDAÇÃO`: quando critérios entrarem em conflito, registrar a ordem de desempate no código, nos testes e no `algorithm_version`.

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
