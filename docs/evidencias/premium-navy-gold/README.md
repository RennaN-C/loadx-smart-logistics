# Redesign premium Navy & Gold — Issue #403

`CONFIRMADO`: base remota `pentest-lab` **49a8ddd90f24ea2e9720bffd208ebb691ec4eb68**,
consultada em 12/11/2026. Branch `feat/premium-frontend-pentest`. A base já contém
v1.3.0; esta entrega mantém a versão e funcionalidades existentes, sem voltar
à v1.2.0 ou transportar commits para main/desenvolvimento.

## Implementação e comparação

As cinco imagens fornecidas no pedido são o alvo de composição. Cada uma foi
examinada individualmente. As capturas abaixo vêm da aplicação executada, não
são geração de imagem, fundos de interface ou métricas fixas.

| Referência | Antes | Depois | Diferenças tratadas |
|---|---|---|---|
| Login | [antes](before-login-desktop.png) | [desktop](after-login-desktop.png), [mobile](after-login-mobile-dark.png) | Cena logística ampla, marca oficial, título dourado, painel de autenticação e animações reais; sem SSO/roteirização/rentabilidade fictícios |
| Visão geral | [antes](before-overview-desktop.png) | [desktop](after-overview-desktop.png), [claro](after-overview-desktop-light.png), [mobile](after-overview-mobile-light.png) | Quatro indicadores, quatro cartões operacionais, duas visualizações de contagens e hierarquia unificada |
| Planejamento | [antes](before-planning-desktop.png) | [desktop](after-planning-desktop.png), [1280](after-planning-1280.png), [mobile](after-planning-mobile-dark.png) | Filtros acima da introdução, identidade/estados/métricas/ações comparáveis, atividade lateral e retomada preservadas |
| Distribuição | [antes](before-distribution-desktop.png) | [desktop](after-distribution-desktop.png), [mobile](after-distribution-mobile-light.png) | Caminhões comparáveis, seleção dourada, ocupação real e 3D integrado |
| Carga 3D | [antes](before-3d-desktop.png) | [desktop](after-3d-desktop.png), [expandido](after-3d-expanded.png), [mobile](after-3d-mobile-light.png) | Cena antes do resultado detalhado, navegação mantida, métricas/controles laterais e cenário navy |

`CONFIRMADO`: paleta, gradientes, bordas e sombras centralizados em `app/styles.css`.
Telas usam os mesmos tokens, incluindo tema claro. Nenhum pacote, contrato HTTP,
RBAC, algoritmo, posição/rotação/dimensão de volume ou modelo de caminhão mudou.
As cores do agrupamento por entrega são preservadas. A paleta decorativa de céu,
chão e grade foi alinhada ao navy; iluminação/câmeras continuam as existentes.

### Animações

Três caminhos SVG locais com traços móveis de 13/16/20 segundos e defasagens,
três nós com pulsação lenta, luz ambiente de 18 segundos e zoom de 26 segundos.
Entradas discretas não atrasam o formulário. Sem timers JS, vídeo ou serviços
externos. O botão pausa sinais, nós, imagem, luz e entradas/reflexo; movimento
reduzido desliga animações e transições. Mobile remove rotas/luz/zoom contínuos.
A imagem fotográfica local existente foi reaproveitada, com proporção preservada;
não é a fotografia exata da referência. O painel não anuncia uma conexão real,
SSO, otimização de rotas ou resultados financeiros inexistentes.

## Validação executada

- Node **22.23.1**, conforme `frontend/.nvmrc`; `npm ci --ignore-scripts` executado.
- `npm run lint`: **0 erros**, duas advertências de Fast Refresh preexistentes em
  `AssistantOperationalCards.tsx`, verificadas também no baseline.
- `npm test -- --run`: **139 arquivos / 1.193 testes aprovados** no código final.
  Inclui MFA, recuperação, dispositivos, navegação, permissões, gráficos e fluxo
  de planejamento. Testes unitários usam doubles conforme padrão da suíte;
  não são apresentados como E2E externo.
- TypeScript/build e validações de rotas Vercel, CSP, fallback e marca aprovados.
  Chunk 3D **230,2 KiB gzip / orçamento 250 KiB**, igual à precisão do baseline.
  Advertência de tamanho bruto do Vite permanece; lazy e gate gzip preservados.
- `npm audit --audit-level=high`: sem alertas altos/críticos; **9 moderados**
  preexistentes nas ferramentas de teste/lint (Vitest/mocker e cadeia minimatch).
  Lockfile inalterado; nenhuma atualização forçada ou gate reduzido.
- Chromium real: **50 combinações** (cinco telas × cinco larguras
  375/768/1024/1440/1920 × claro/escuro), sem overflow horizontal, além de
  screenshots desktop 1672×941 para comparação e 1280×900 para planejamento.
- Cinco perfis: ADMIN/LOGISTICS_MANAGER/CHECKER acessam planos; DRIVER/CUSTOM sem
  concessão não acessam. Drawer mobile e Escape verificados nos cinco.
- Login inválido contra backend real; login válido CHECKER e F5; recuperação por
  navegação, notificações e busca com endpoint real. Pausa/retomada e movimento
  reduzido verificados por animações computadas, não só por classes CSS.
- Troca de caminhão e F5, uma cena no expandido, Escape, ângulo lateral e sequência
  de carregamento executados. Nenhum erro de página no registro da matriz.

### Dados e limites da evidência

`CONFIRMADO`: API local com PostgreSQL 16 exclusivo `loadx_premium_qa`, migrations
até `20261023_0035`, dados sintéticos. Distribuição de 40 volumes em dois caminhões
e plano individual de 18 volumes criados por contratos reais; dois carregamentos
conferidos, uma viagem programada e outra finalizada com entrega pelas APIs.
Os resultados/estados das capturas são do banco, não valores das imagens alvo.
Fixtures de preparação usam helpers existentes; sessões dos cinco perfis são
sintéticas. O login CHECKER adicional usa senha/sessão reais só desse banco isolado.
Nenhum banco compartilhado ou credencial publicada foi usado.

`RISCO IDENTIFICADO`: renderização usa SwiftShader; não mede FPS/GPU física nem
prova performance em todo dispositivo. Não houve novo aceite externo de MFA,
e-mail ou de todas as 39 telas. A suíte protege seus contratos; o escopo visual
comparado aqui é exatamente as cinco referências. Não se afirma igualdade pixel
a pixel: fotografia e modelo 3D existentes foram mantidos e dados têm outras
contagens reais. Revisão visual final pelo responsável continua recomendada.

## Publicação

`CONFIRMADO`: o workflow geral não inclui PR/push para pentest-lab. As verificações
frontend equivalentes acima foram executadas localmente; ausência de check não
é aprovação de CI. Segurança/backend não foi enfraquecida nem reconfigurada.
Nenhuma mudança backend/migration ou novo deploy Render é necessário.

Saúde pública consultada: `/health` HTTP 200 e `/ready` HTTP 200, após primeira
consulta atingir timeout de 20s (serviço respondeu na tentativa posterior).
O token GitHub disponível recebe 403 em deployments/branch-protection; não
permite inspecionar esses metadados. Status Vercel/checks da PR e validação HTTP
devem comprovar o SHA antes de afirmar publicação. Resultado final de integração
fica no corpo da PR/Issue para não versionar uma confirmação antes de ocorrer.
