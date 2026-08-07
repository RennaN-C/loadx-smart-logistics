# Componentes compartilhados

Botões, campos, tabelas, modal, badge de status, feedback de erro e outros componentes reutilizados por várias features.

Componentes usados por apenas uma feature permanecem dentro dela.

## O que existe hoje

- `Modal.tsx`: overlay + diálogo acessível (`role="dialog"`), fecha no Escape e no clique fora.
- `StatusPill.tsx`: badge de status com tom `good`, `warn` ou `neutral`.
- `AlertBanner.tsx`: faixa de erro com `role="alert"`.
- `Tabs.tsx`: barra de abas acessível (`role="tablist"`), controlada por quem usa.
- `FormField.tsx`: rótulo + controle + dica opcional, com o `htmlFor` já ligado.

As classes visuais desses componentes, junto de `.btn-primary`, `.btn-secondary`, `.btn-link` e
`.field-label`, ficam em `app/styles.css` — o CSS global é o único lugar que essas classes existem.

> A `LoginForm` (OC24) ainda usa as classes próprias dela (`.login-alert`, `.login-submit`).
> Migrá-la para estes componentes é uma limpeza pendente, deixada de fora da OC26 de propósito.
