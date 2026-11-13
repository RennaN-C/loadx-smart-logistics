# Refinamento do login — Issue #409

`CONFIRMADO`: base `pentest-lab` **c4bd59e8**, branch
`correcao/login-alta-definicao`. Escopo visual autorizado pelo responsável em
12/11/2026. Sem alterações em main/desenvolvimento, backend, Render, banco,
contratos HTTP ou regras de autenticação.

`CONFIRMADO`: a causa anterior era o uso de um AVIF 1006×941 com marca, título
e ícones rasterizados, `object-fit: fill` e textos HTML ocultos no desktop.
A solução usa foto limpa, mapa SVG geográfico, marca SVG e texto HTML em
camadas. O CSS foi consolidado por componente, com dois breakpoints locais.

`CONFIRMADO`: foto gerada novamente, **1606×979 px nativos**, WebP qualidade 94,
e redução 1024×624 para `srcset`. Sem upscale, blur ou distorção. A fotografia
ocupa 60% da largura e os 65% inferiores da altura no desktop, portanto cabe
em sua resolução nativa no viewport 2560×1440 em 1× (área 1536×936).
Marca e textos permanecem vetoriais em qualquer densidade. Proveniência,
fonte do mapa e prompt final no [README dos assets](../../../frontend/public/images/README.md).

`RISCO IDENTIFICADO`: a ferramenta não entregou os 2560–3200 px preferidos.
Não se afirma que a fotografia é 4K ou atende densidade 2× nativa em QHD.
A reconstrução altera detalhes do caminhão/galpão; não é reprodução pixel a
pixel da arte. A referência inclui SSO e roteirização externa; esses elementos
não foram adicionados. Os diferenciais usam capacidades existentes e o rodapé
orienta contato com o administrador, conforme pedido.

## Evidências visuais

`CONFIRMADO`: capturas reais Chromium **156.0.8078.4**, frontend Vite local,
API interceptada com contratos existentes e dados fictícios. A execução não
acessa backend, não envia e-mail nem autentica conta remota.

| Captura | Verificação |
| --- | --- |
| [Referência × resultado](comparison-reference.png) | Comparação lado a lado da composição |
| [Antes × depois](comparison-before.png) | AVIF esticado × camadas nítidas |
| [1366×768](login-1366x768.png) | Formulário inteiro no desktop menor |
| [1600×900](login-1600x900.png) | Composição e tipografia |
| [1920×1080](login-1920x1080.png) | Tema do sistema claro; acesso preserva navy aprovado |
| [2560×1440](login-2560x1440.png) | Foto em resolução nativa, logo/textos vetoriais |
| [820×1180](login-820x1180.png) | Breakpoint compacto |
| [375×667](login-375x667.png) | Mobile com rolagem vertical acessível |
| [320×568](login-320x568.png) | Largura mínima, sem overflow horizontal |
| [Erro](login-error-1366.png) | Mensagem e possibilidade de nova tentativa |
| [Recuperação](recovery-1366.png) | Resposta neutra do contrato simulado |
| [MFA](mfa-1366.png) | Desafio preservado, opt-in desmarcado |

`CONFIRMADO`: revisão manual das comparações verificou caminhão, mapa,
tipografia, escala, enquadramento, iluminação e card. A faixa da fotografia foi
reenquadrada para eliminar uma emenda encontrada na primeira iteração. O mapa
foi reposicionado para manter os arcos no céu. A legenda adicional solicitada
ocupa espaço entre o título e os diferenciais; não existia na arte conceitual.

`CONFIRMADO`: [resultados automatizados](browser-results.json) contêm boxes
reais e asserções de proporção (âncoras da referência), ausência de overflow,
`cover`, ausência de filtros, marca SVG, foco e texto visível. Não se usa um
limiar de pixel diff: comparar foto reconstruída e conceito com funcionalidades
distintas dessa maneira não comprovaria fidelidade nem funcionalidade.

## Testes e reprodução

`CONFIRMADO`: Node **22.23.1** da `.nvmrc`, dependências do lockfile inalteradas.

- `npm ci --ignore-scripts`: passou; auditoria reportou 9 vulnerabilidades moderadas na árvore existente.
- `npm run lint`: passou, 0 erros; 2 avisos preexistentes em `AssistantOperationalCards.tsx`.
- `npm test -- --run`: **139 arquivos / 1193 testes passaram**.
- `npm run build`: passou, incluindo TypeScript, orçamento 3D, proxy/CSP e marca/assets.
- Chromium: **7 viewports, 6 fluxos**, sem erros JavaScript não tratados.

`CONFIRMADO`: os fluxos de navegador cobrem obrigatoriedade, erro de login,
alternância da senha, recuperação, redefinição com remoção do fragmento,
MFA com opt-in desmarcado e retorno ao destino protegido. A suíte existente
também cobre AuthProvider, RequireAuth, MFA/provisionamento e recuperação.

Para reproduzir, iniciar o frontend e executar na raiz com Playwright instalado
como ferramenta de desenvolvimento externa à aplicação:

```powershell
$env:PLAYWRIGHT_MODULE = '<caminho do módulo playwright instalado>'
$env:LOGIN_URL = 'http://127.0.0.1:5174'
node docs/evidencias/login-alta-definicao/verify.cjs
$env:LOGIN_REFERENCE = '<caminho do PNG aprovado>'
node docs/evidencias/login-alta-definicao/compare.cjs
```

`CONFIRMADO`: `BASELINE_URL` opcional captura o commit-base em servidor
separado. `before-1600x900.png` foi capturado desse commit, não reconstruído
manualmente. Os scripts não persistem credenciais nem registram fatores reais.

`PENDENTE DE DEFINIÇÃO`: um teste autenticado contra conta remota autorizada
não foi executado; os ensaios com API simulada não certificam cookies, banco,
SMTP ou MFA do ambiente publicado. A inspeção pública após deploy deve
confirmar o SHA/READY, assets e formulário sem afirmar login real de usuário.
