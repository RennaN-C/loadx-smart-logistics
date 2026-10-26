# Login profissional — 25/10/2026

`CONFIRMADO`: Issue #304, refinamento visual solicitado pelo responsável.

## Mudanças

- Painel navy com malha discreta, profundidade e composição em duas colunas.
- Ilustração SVG própria de caminhão e volumes, com fluxo luminoso e movimento
  suave. É arte decorativa, sem métricas operacionais ou rastreamento real.
- Formulário com hierarquia mais clara, foco dos campos, hover e brilho no botão.
- Controle acessível Pausar/Ativar efeitos; prefers-reduced-motion desativa
  movimento e transições. No celular, a marca fica compacta e o acesso tem prioridade.
- CSS anterior e suas sobrescritas foram consolidados em um único layout.
- Autenticação, MFA, recuperação, cookies, CSRF e redirecionamentos preservados.

Arquivos principais: LoginPage.css, BrandPanel.tsx, LoginIllustration.tsx,
LoginForm.tsx e teste do controle de movimento. README de auth atualizado.
O relatório de prontidão também foi atualizado com Issues/PRs consultados em
25/10/2026: [o que falta para v1.2.0](../../releases/v1.2.0-readiness.md).

## Validação

`CONFIRMADO`: 85 testes da feature auth aprovados, incluindo login, desafio
MFA, recuperação e o novo controle Pausar/Ativar. ESLint e build aprovados;
orçamento LoadViewer de 229,6 KiB gzip permanece abaixo de 250 KiB. O aviso
existente de tamanho de chunks continua sendo emitido pelo build.

`CONFIRMADO`: 48 verificações Chromium das rotas locais de login, recuperação e
reset, combinando quatro larguras (1600, 1280, 768, 375 px), dois temas e duas
preferências de movimento. Sem overflow global ou erro JavaScript fatal. O
controle pausa a animação e a preferência reduzida resulta em animation-name none.
Capturas finais aguardam o término da transição de entrada.

`CONFIRMADO`: não houve mocks de HTTP nessa verificação visual. Nenhuma senha
foi submetida nem e-mail de recuperação enviado. O reset foi aberto sem token,
para verificar a apresentação de seu estado inicial; isso não testa entrega de
e-mail ou consumo real de token. O ensaio real anterior de senha/MFA e operação
está em [usabilidade local](../usabilidade-local/README.md).

## Capturas

| Tema | Desktop | Celular |
| --- | --- | --- |
| Escuro | [1600 px](login-dark-1600.png) | [375 px](login-dark-375.png) |
| Claro | [1600 px](login-light-1600.png) | [375 px](login-light-375.png) |

Matriz completa: [results.json](results.json).

`CONFIRMADO`: esta alteração não publica a v1.2.0, não implanta em homologação
e não encerra pendências de aceite externas ou de avaliação humana.

`CONFIRMADO`: suíte frontend completa com 1.130 testes aprovados. Mais três
checagens de altura compacta (1366×768, 1280×720, 375×667) confirmaram formulário
inteiro visível sem rolagem, além da matriz principal. Capturas:
[notebook](login-dark-1366x768.png), [celular compacto](login-dark-375x667.png).
[Resumo de validação](validation.json) e [dimensões medidas](compact-viewports.json).
