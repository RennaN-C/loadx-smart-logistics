# Ensaio técnico para gravação local — 25/10/2026

`CONFIRMADO`: Issue #302. Os cinco pontos receberam entregas verificáveis:

| Ponto | Entrega | Verificação |
| --- | --- | --- |
| Impedir cálculo inviável conhecido | Preflight obrigatório da seleção atual | Testes de pendência, erro, frota vazia, resposta antiga e atualização |
| Explicar ações bloqueadas | Mensagens específicas ligadas por aria-describedby | Testes e [captura](clear-disabled-action.png) |
| Dados próprios para gravar | Script local por lote e manifesto gravacao-01 | Duas execuções com mesma saída; três veículos e três motoristas livres |
| Ensaio com autenticação real | Senha, cadastro MFA e TOTP pela interface | Ciclo completo no navegador, HTTP real e conferência de estados no banco |
| Tarefas e observação | Roteiro neutro e ficha em branco | [Material de gravação](../../usabilidade/README.md) |

## Fluxo real verificado

`CONFIRMADO`: conta fictícia dedicada, perfil ADMIN. O cadastro da conta usa o
serviço administrativo existente. O acesso no navegador é liberado por senha e
MFA/TOTP reais. Não há mocks de HTTP, substituição de dependências, sessão
forjada ou alteração das regras de autenticação. A sessão usada no ensaio foi
obtida pelo login e reutilizada pelo navegador como uma sessão normal.

1. Pedido cadastrado pela interface, com seis volumes e destino fictício.
2. Pedido alterado para Pronto pelo formulário de edição.
3. Planejamento em um veículo, cálculo persistido e cena 3D real consultada.
4. Plano aprovado e carregamento criado pela interface.
5. Conferência dos seis volumes, individualmente, e carregamento finalizado.
6. Viagem criada com motorista elegível, iniciada e entrega confirmada.
7. Viagem finalizada; pedido consultado como Entregue.
8. Estados relidos no PostgreSQL: pedido DELIVERED, carregamento FINISHED,
   viagem FINISHED e todas as suas entregas DELIVERED.

`CONFIRMADO`: além do fluxo simples, o pedido MULTI do lote de ensaio foi
selecionado na interface; preflight real consultado; proposta automática salva
com dois caminhões e 24 identidades físicas distintas. A proposta foi deixada
PROPOSED, sem iniciar operações. Desktop e celular sem overflow global.

`CONFIRMADO`: o primeiro ensaio foi retomado após ajustes nos seletores do
driver de teste; não houve correção de regra operacional para fazê-lo passar.
Um segundo fluxo simples foi executado do começo ao fim em uma única rodada.
Os resultados desse segundo fluxo são os publicados aqui. No navegador não
foram observados erros JavaScript fatais nesse percurso.

## Resultados e capturas

- [Resultados estruturados, requisições e prova de estados no banco](results.json).
- [Cena 3D](single-3d.png).
- [Carregamento concluído](loading-finished.png).
- [Viagem finalizada](trip-finished.png).
- [Pedido entregue](order-delivered.png).
- [Consulta real de frota](eligible-fleet.png).
- [Distribuição em dois caminhões](multi-real-desktop.png) e [celular](multi-real-mobile.png).

`CONFIRMADO`: 1.129 testes frontend e 11 testes unitários dos scripts aprovados.
ESLint e build aprovados, incluindo orçamento obrigatório do bundle. Ruff
aprovado nos arquivos Python alterados. O aviso existente de tamanho de chunks
permanece; o orçamento do LoadViewer passa.

## Limites e preparação da gravação

`CONFIRMADO`: o ensaio é técnico e automatizado. Não mede facilidade percebida,
tempo humano ou compreensão de participantes. A ficha permanece em branco.
API, backend e PostgreSQL utilizados são locais; isso não homologa o ambiente
publicado. Não houve aumento do limite de volumes, mudança de schema, regras
físicas, contratos HTTP ou integrações externas.

`CONFIRMADO`: o lote gravacao-01 foi preparado separadamente, com dois pedidos
prontos e um rascunho, sem planos criados para esses pedidos. A disponibilidade
é uma fotografia e precisa ser conferida novamente se o usuário operar os dados
antes de gravar. O script não desfaz alterações para repetir uma tomada.

`CONFIRMADO`: nomes nas capturas são fictícios. Senhas, cookies, segredos TOTP,
QR de cadastro e códigos de recuperação não fazem parte dos artefatos. A conta
técnica dedicada é desativada ao concluir o ensaio, pelo serviço existente.
