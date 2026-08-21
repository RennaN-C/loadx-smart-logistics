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

> A `LoginForm` (OC24) ainda usa as classes próprias dela (`.login-alert`, `.login-submit`).
> Migrá-la para estes componentes é uma limpeza pendente, deixada de fora da OC26 de propósito.
