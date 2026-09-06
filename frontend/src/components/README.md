# Componentes compartilhados

Botões, campos, tabelas, modal, badge de status, feedback de erro e outros componentes reutilizados por várias features.

Componentes usados por apenas uma feature permanecem dentro dela.

## O que existe hoje

- `Modal.tsx`: overlay + diálogo acessível (`role="dialog"`), fecha no Escape e no clique fora.
- `StatusPill.tsx`: badge de status com tom `good`, `warn` ou `neutral`.
- `AlertBanner.tsx`: faixa de erro com `role="alert"`.
- `Tabs.tsx`: barra de abas acessível (`role="tablist"`), controlada por quem usa.
- `FormField.tsx`: rótulo + controle + dica opcional, com o `htmlFor` já ligado.
- `Pagination.tsx`: navegação entre páginas a partir dos metadados da ADR-017; some sozinha quando há uma página só.
- `Icon.tsx`: conjunto de ícones e a marca da LoadX, desenhados aqui.
- `Avatar.tsx` + `initials.ts`: âncora visual com as iniciais de uma pessoa ou empresa.
- `Tooltip.tsx`: dica de contexto sob demanda, no `i` ao lado do rótulo.
- `masks.ts`: máscaras de CPF, CNPJ e telefone. **Funções puras, testadas.**

## Máscaras: por que dígitos viajam e pontuação fica na tela

A formatação é PROGRESSIVA — "1234" vira "123.4" — porque máscara que só aparece
no fim faz o campo dar um pulo visual ao completar, e quem digita perde a
referência.

O que vai para a API são os DÍGITOS, sem pontuação. O backend guarda `document`
como texto livre de até 32 caracteres e compara unicidade como string
(`customers/schemas.py`): gravar ora com máscara ora sem deixaria o mesmo CPF
entrar duas vezes.

A validação confere só o TAMANHO, sem dígito verificador. Conferir o dígito
recusaria documento fictício de teste e deixaria o frontend mais rígido que o
contrato — passaria a rejeitar cadastro que a API aceitaria.

## Tooltip: por que não é o `title` nativo

O `title` não aparece para quem navega por teclado, demora quase um segundo
para surgir e não é estilizável. A dica aqui explica FORMATO de campo, que é
o que a pessoa precisa ler antes de digitar, então abre no mouse e no foco.

O gatilho é um `<button>` de verdade, porque precisa receber foco, e
`aria-describedby` liga a bolha a ele — o leitor de tela anuncia a explicação
junto do botão em vez de tratá-la como texto solto.

A bolha abre para cima, para não tapar o campo, e vira para baixo quando não há
espaço. Isso importa dentro do modal: `.modal-overlay` usa `overflow: auto`,
então uma bolha que subisse além do topo seria recortada em vez de rolar.
Medido nos dois modos com o CSS real: sempre inteira dentro da janela.

## Por que os ícones são desenhados no projeto

São poucos e cada um pesa algumas centenas de bytes; trazer um pacote inteiro só por causa de
desenho não se paga — foi o mesmo raciocínio que tirou o drei da visualização 3D. Todos partilham a
grade de 24 e o traço de 1.75, e é essa repetição que faz o conjunto parecer uma família só.

Os ícones são **sempre decorativos** (`aria-hidden`), porque em todo lugar onde aparecem há um
rótulo em texto junto — quando o rótulo não cabe na tela, como no botão de sair, ele continua lá
via `.sr-only`. Ícone que carrega significado sozinho precisa de nome acessível, e quem deve
fornecer é o componente que usa, não o `Icon`.

Como não dá para revisar SVG lendo o `d` do path, a geometria dos onze foi medida com `getBBox()`:
todos ficam dentro da grade de 24 e nenhum é degenerado.

As classes visuais desses componentes, junto de `.btn-primary`, `.btn-secondary`, `.btn-link` e
`.field-label`, ficam em `app/styles.css` — o CSS global é o único lugar que essas classes existem.

## O que a LoginForm reaproveita, e o que não

`CONFIRMADO`: a `LoginForm` (OC24) usa `AlertBanner` e `.btn-primary`. O `.login-alert` era um
duplicado exato do `.alert-banner` e saiu; o `.login-submit` era o `.btn-primary` reescrito e ficou
só com o que difere de verdade — largura do cartão e anel de foco escuro, porque o anel laranja
padrão sumiria contra o fundo do próprio botão.

Os CAMPOS continuam próprios, de propósito. O `FormField` põe rótulo, controle e dica em coluna, e o
campo de senha do login tem um botão "mostrar" na mesma linha do rótulo. Encaixá-lo no `FormField`
exigiria abrir o componente para um caso que só existe aqui — sai mais caro do que as poucas linhas
que ele economizaria.
