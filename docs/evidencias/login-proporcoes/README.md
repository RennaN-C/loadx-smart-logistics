# Proporções do painel de login — Issue #411

`CONFIRMADO`: base `pentest-lab` **44eb90b2**, branch
`correcao/proporcoes-painel-login`. Mudança solicitada pelo responsável em
12/11/2026, restrita ao tamanho, tipografia e espaçamentos do card direito.

`CONFIRMADO`: o único arquivo de implementação alterado é
`frontend/src/features/auth/pages/LoginPage.css`. O README da feature e esta
pasta documentam o resultado. Componentes TSX, assets, dependências, cores,
gradientes, `Identity.css`, rotas, backend e banco permanecem sem alterações.

`CONFIRMADO`: removido o mínimo de 87svh; card desktop com até 510 px,
padding 36×40 px, gap 18 px e raio 20 px; título limitado a 28–34 px,
marca 52 px, campos 50 px e botão 52 px. Rodapé com margem fixa de 6 px.
As declarações substituídas foram retiradas dos estilos base. Desktop e mobile
ficam em blocos próprios, sem acumular versões no fim do arquivo.

`CONFIRMADO`: `form.login-card` sozinho também seleciona MFA e recuperação.
O seletor desktop usa `:not(.identity-card)` e a coluna usa `:has()` para
aplicar padding simétrico apenas ao formulário de entrada. Os demais tamanhos
continuam sob `Identity.css`. O mobile preserva os valores anteriores.

## Medidas reais do navegador

| Viewport | Card anterior (largura × altura) | Card atual | Título atual |
| --- | --- | --- | --- |
| 1366×768 | 497×668 px | 482×594 px | 28 px |
| 1600×900 | 582×783 px | 510×599 px | 32 px |
| 1920×1080 | 698×940 px | 510×601 px | 34 px |
| 2560×1440 | 931×1253 px | 510×601 px | 34 px |
| 375×667 | 347×617 px | 347×617 px | 23 px (inalterado) |

`CONFIRMADO`: card centralizado horizontalmente na coluna direita e
verticalmente no viewport (tolerância <1 px). Em 1366×768 permanece inteiro,
com 87 px acima/abaixo, título 28 px, inputs 50 px e botão 52 px. Não há
overflow horizontal. O mobile mantém a rolagem vertical anterior.

## Capturas e comparação

| Resolução | Antes | Depois | Comparação |
| --- | --- | --- | --- |
| 1366×768 | [Captura](before-1366x768.png) | [Captura](after-1366x768.png) | [Lado a lado](comparison-1366x768.png) |
| 1600×900 | [Captura](before-1600x900.png) | [Captura](after-1600x900.png) | [Lado a lado](comparison-1600x900.png) |
| 1920×1080 | [Captura](before-1920x1080.png) | [Captura](after-1920x1080.png) | — |
| 2560×1440 | [Captura](before-2560x1440.png) | [Captura](after-2560x1440.png) | [Lado a lado](comparison-2560x1440.png) |
| 375×667 | [Captura](before-375x667.png) | [Captura](after-375x667.png) | Hashes idênticos |

`CONFIRMADO`: capturas reais Chromium 156.0.8078.4, Node 22.23.1,
frontend Vite local e API simulada com dados fictícios. Sem envio de e-mail
nem credenciais reais. Fontes carregadas explicitamente e ponteiro fora dos
botões para evitar diferenças de fallback tipográfico ou hover.

`CONFIRMADO`: hashes do painel esquerdo coincidem nas cinco resoluções,
isolando a sombra do card direito que ultrapassa a emenda das colunas.
O screenshot inteiro do mobile é idêntico. Os cards de
[recuperação antes](before-recovery-1920.png)/[depois](after-recovery-1920.png) e
[MFA antes](before-mfa-1920.png)/[depois](after-mfa-1920.png) têm medidas,
tipografia e pixels idênticos em 1366 e 1920 px. O script também verifica
foco visível e alternância da senha sem apagar o valor.
[Resultados completos](results.json).

## Testes e reprodução

`CONFIRMADO`:

- `npm run lint`: passou, 0 erros, 2 avisos preexistentes em `AssistantOperationalCards.tsx`.
- `npm test -- --run`: 139 arquivos / **1193 testes passaram**.
- `npm run build`: passou, incluindo TypeScript e gates de bundle, rotas/CSP e marca.
- `verify.cjs`: cinco viewports sem overflow, centralização e áreas de clique; cenário/mobile e cards MFA/recuperação preservados.

Para reproduzir na raiz, com Playwright instalado como ferramenta externa e
servidores separados para base e alteração:

```powershell
$env:PLAYWRIGHT_MODULE = '<caminho do módulo playwright>'
$env:BASELINE_URL = 'http://127.0.0.1:5175'
$env:LOGIN_URL = 'http://127.0.0.1:5174'
node docs/evidencias/login-proporcoes/verify.cjs
node docs/evidencias/login-proporcoes/compare.cjs
```

`RISCO IDENTIFICADO`: a comparação binária do cenário é feita sem a sombra
do card direito; essa sombra muda de alcance ao reduzir/centralizar o card.
Os arquivos do cenário e seus estilos não foram alterados. Testes com API
simulada não certificam autenticação, cookies, SMTP ou MFA do serviço remoto.

`PENDENTE DE DEFINIÇÃO`: conferir CI, integração e SHA/READY da Vercel após
abrir o PR. O resultado dessa etapa deve constar no corpo atualizado do PR.
