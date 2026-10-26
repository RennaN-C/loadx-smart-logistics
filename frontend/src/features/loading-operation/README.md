# Feature: loading-operation

Conferência do carregamento (OC32) com leitura de QR Code ou código de barras
(OC75), consumindo o backend da OC76.

## Como se chega aqui

`CONFIRMADO`: pelo plano de carga **aprovado**. `StartLoadingAction` chama
`POST /loading-sessions`, que **cria ou devolve** a única sessão do plano, e
navega para `/loading/:sessionId`. Como a chamada é idempotente, o mesmo botão
serve para abrir e para voltar, e nenhuma tela precisa guardar o id da sessão.

`RISCO IDENTIFICADO`: **não existe rota de listagem de sessões**, e o plano não
expõe o id da sessão. Só `LOGISTICS_MANAGER` pode criar — então o `CHECKER`,
que é justamente quem opera esta tela, não tem como encontrar o próprio
carregamento pela interface: ele depende de receber o link. É a mesma lacuna
que o motorista teve antes de existir `GET /trips`. Resolver exige backend: ou
uma listagem recortada por perfil, ou o id da sessão no próprio plano.

## Permissões (OC66)

| | `ADMIN` | `LOGISTICS_MANAGER` | `CHECKER` | `DRIVER` |
|---|---:|---:|---:|---:|
| Ver o checklist | Sim | Sim | Sim | Não |
| Criar a sessão | Não | Sim | Não | Não |
| Iniciar, conferir e finalizar | Não | Não | Sim | Não |

`ADMIN` e `LOGISTICS_MANAGER` veem o checklist sem nenhuma ação na tela.
Esconder o botão **não** substitui o backend, que continua respondendo `403`;
evita apenas oferecer um caminho que terminaria em recusa.

## Leitura de código

`CONFIRMADO`: o código é `loadx:loading-item:<uuid>`, 55 caracteres, e vem
pronto do backend em `items[].code`. O frontend **nunca monta** esse texto nem
extrai o UUID: manda de volta exatamente o que leu. Quem decide qual volume o
código identifica é o servidor — repetir essa decisão aqui abriria espaço para
a tela marcar um item que o backend recusaria. Código é identidade, não
autorização.

O campo é um `<form>` com entrada de texto, não um componente de câmera: um
leitor físico se comporta como teclado, digita o código inteiro e termina com
Enter. O mesmo campo atende quem digita à mão quando a etiqueta está danificada
— o caminho manual que a OC75 manda preservar, junto do botão "Conferir" de
cada linha.

O foco **volta para o campo** depois de cada leitura. Sem isso é preciso clicar
entre um volume e outro, o que inviabiliza o uso com o leitor na mão.

Há uma checagem de formato antes da requisição. Ela **não substitui** a
validação do servidor: serve para não gastar uma ida ao backend com algo que
nem parece um código deste sistema, e para responder na hora. O padrão aceito é
o mesmo do backend — prefixo literal e UUID canônico **minúsculo**.

### Erros, e o que cada um diz

Cada caso do contrato tem uma frase própria. O conferente está de pé ao lado do
caminhão: "conflito" o obrigaria a parar e perguntar para alguém.

| Código | O que a tela diz |
|---|---|
| `LOADING_ITEM_NOT_FOUND` | Nenhum volume corresponde a este código |
| `LOADING_ITEM_SESSION_MISMATCH` | O volume é de **outro** carregamento; nada foi conferido |
| `LOADING_ITEM_ALREADY_CHECKED` | Já estava conferido; a leitura não mudou nada |
| `LOADING_STATUS_TRANSITION_NOT_ALLOWED` | A ação não vale para a etapa atual |
| `LOADING_CHECKLIST_INCOMPLETE` | Ainda há volumes pendentes |

`CONFIRMADO`: erro nenhum altera o checklist, e a tela reflete isso — em caso
de falha, nada muda na lista.

## O nome do produto vem do plano

`loading_session_items` guarda só `id`, `load_plan_item_id` e `status`. Um
checklist de UUIDs não serve para quem confere caixa por caixa, então
`useLoadingSession` junta com os itens do plano por `load_plan_item_id`. É
junção de **apresentação**: nada aqui decide o que pode ser conferido.

A ordem é a de **carregamento**, calculada pelo backend — a ordem em que os
volumes entram no caminhão, que é como o conferente os encontra na doca.

Se o plano não carregar, o volume continua na lista e continua conferível, só
sem o nome do produto. Uma linha a menos faria o checklist mentir sobre quantos
volumes existem.

## Nenhum contador é calculado aqui

Todas as rotas — inclusive conferir item e ler código — devolvem a **sessão
inteira**. Pendentes, "pode finalizar" e situação de cada linha saem da lista
que o backend recalculou, então não há estado derivado no cliente para
divergir.

## Estrutura

- `api/loadingApi.ts`: as cinco chamadas do módulo.
- `hooks/useLoadingSession.ts`: carga da sessão, junção com o plano, transições.
- `components/ScanField.tsx`: leitura e digitação do código.
- `components/LoadingChecklist.tsx`: a lista e a conferência manual.
- `components/StartLoadingAction.tsx`: porta de entrada no plano aprovado.
- `components/loadingErrorMessages.ts`: mensagens e validação de formato.
- `pages/LoadingPage.tsx`: a tela.

## Retorno e recuperação (#188)

`CONFIRMADO`: `/loading/:sessionId` mostra o link permanente e caminhos para
início e plano de origem. Após finalizar, ADMIN/LOGISTICS_MANAGER recebem o
caminho para criar a viagem no plano. A tabela possui rolagem horizontal própria
com região identificada e foco pelo teclado. Trocar a sessão limpa os itens e
ignora respostas de ações anteriores. A listagem geral permanece pendente dos
contratos e da OC93; ver [fluxo operacional](../../../../docs/06-fluxo-operacional.md).
