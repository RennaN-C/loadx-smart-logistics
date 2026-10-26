# Login fotográfico — Issue #306

CONFIRMADO: revisão solicitada pelo responsável em 25/10/2026 após rejeitar o desenho de caminhão. A composição substitui SVG e moldura por uma imagem própria de aparência fotográfica no painel inteiro, com gradientes, tipografia e etapas discretas. O formulário mantém a identidade navy/âmbar e os temas.

CONFIRMADO: arte gerada com a ferramenta integrada `imagegen`; arquivo, dimensões, modo e prompt final em [frontend/public/images/README.md](../../../frontend/public/images/README.md). Não há hotlink ou biblioteca adicional. A imagem é decorativa, não representa operação real.

## Verificações

CONFIRMADO: `validation.json` registra 1.130 testes frontend e 85 de autenticação aprovados, lint, build e orçamento de bundle. Após reforçar as asserções de pausa/retomada, os dois testes de BrandPanel passaram novamente.

CONFIRMADO: Playwright/Chromium contra `http://localhost:5173`, sem mocks de rotas, exercitou login, recuperação e redefinição: dois temas × quatro larguras (1600, 1280, 768, 375) × dois modos de movimento × três rotas = 48 verificações. O script aguardou decodificação da imagem; nenhuma imagem ausente, erro JavaScript ou rolagem horizontal foi encontrado. A pausa e retomada da animação foram verificadas pelo estilo computado. A pausa durante a entrada manteve o texto visível. Não foram enviadas credenciais ou mensagens de recuperação.

CONFIRMADO: `compact-viewports.json` verifica formulário inteiramente visível e ausência de rolagem horizontal/vertical em 1366 × 768, 1280 × 720 e 375 × 667. As capturas aguardaram fontes, imagem e conclusão da transição de entrada.

CONFIRMADO: revisão React verificou semântica, imagem decorativa, prioridade de carregamento, dimensões explícitas, estado local e atualização funcional do controle de pausa. A animação usa somente transformação CSS e respeita `prefers-reduced-motion`.

## Capturas

- [Desktop escuro](login-dark-1600.png) e [claro](login-light-1600.png).
- [Celular escuro](login-dark-375.png) e [claro](login-light-375.png).
- [Notebook 1366 × 768](login-dark-1366x768.png) e [celular 375 × 667](login-dark-375x667.png).

RISCO IDENTIFICADO: o build mantém aviso preexistente de chunk 3D grande; o orçamento obrigatório continua aprovado. Estas verificações visuais e testes de auth não substituem nova avaliação humana de usabilidade ou o aceite final da release.
