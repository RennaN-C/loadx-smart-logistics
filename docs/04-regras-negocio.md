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

`PENDENTE DE DEFINIÇÃO`: matriz detalhada de permissões por endpoint.

## Autenticação

- Usuário deve autenticar com e-mail e senha.
- Senha deve ser persistida somente como hash.
- Respostas públicas de usuário nunca devem retornar `password_hash`.
- Token JWT deve identificar o usuário pelo UUID em `sub`.
- Usuário inativo não pode fazer login.

`SUPOSIÇÃO TÉCNICA`: o backend usa `pbkdf2_sha256` via Passlib para hash de senha nesta etapa, evitando incompatibilidade local do bcrypt no ambiente Python usado para testes.

`PENDENTE DE DEFINIÇÃO`: política final de expiração, refresh token, bloqueio por tentativas inválidas e força mínima de senha.

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
