# Imagem do login

## Asset corrente — Issue #409, 12/11/2026

`CONFIRMADO`: `login-scene-hd.webp` é uma reconstrução própria feita com a
ferramenta integrada `imagegen`, usando a referência aprovada anexada pelo
responsável. **1606×979 px nativos**, 286.622 bytes, WebP qualidade 94, sem
textos, logotipos ou mapa incorporados. `login-scene-1024.webp` é somente uma
redução responsiva para 1024×624 (144.886 bytes). Nenhum upscale foi utilizado.
A foto é exibida na faixa inferior de 65% do painel; um pequeno fade de alpha
no céu integra a borda superior. Não há blur, filtro ou `object-fit: fill`.

`CONFIRMADO`: `login-globe.svg` é um mapa estático com projeção ortográfica
centrada em longitude −63°, latitude 5°, costa/fronteiras reais, pontos pequenos
e arcos decorativos. Fonte:
[Natural Earth 1:50m, países](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson),
em [domínio público](https://www.naturalearthdata.com/about/terms-of-use/).
O SVG não usa fonte raster, scripts ou requests externos. As conexões não
representam rotas calculadas pelo sistema. A máscara limita o mapa ao céu.
A marca vetorial fica em `../branding/loadx-login-mark.svg`, reproduzindo
o símbolo do conceito aprovado somente nas telas de acesso; o BrandMark
compartilhado das demais telas não foi alterado.

`RISCO IDENTIFICADO`: a ferramenta integrada não respeitou o alvo de saída
2560–3200 px. Foram descartadas variantes de enquadramento inadequado. O asset
final cobre o painel fotográfico de 1536×936 em viewport 2560×1440 a 1×,
mas não equivale a foto nativa 4K/2×. A reconstrução preserva o enquadramento
geral e a iluminação, com diferenças nos detalhes do veículo/galpão.

Prompt final, ferramenta integrada, imagem de referência fornecida, fundo opaco:

> Asset: clean photographic login background, landscape ratio 1.64:1, 2560x1560 requested. This is ONLY the bottom 65% of the LEFT 60% of the reference, from the warehouse roof at y35% of the original to the pavement at the bottom. Preserve exact reference composition and truck angle. Critical framing: warehouse roof starts at very top-left (0%,0%) and slopes down toward (55%,35%); clean deep navy sky above that roof at top right. Black truck roof at (58%,25%), bottom of tires at y84%; trailer occupies x33-69%, cabin x69-91%, forklift x2-17% with bottom at y83%. Wet pavement and reflections from y84% to100%. Keep entire truck and forklift, no excessive foreground. Black cab-over semi, black trailer with restrained gold diagonal stripes, warehouse docks amber interior lighting, sunset at far right, blue/gold cinematic commercial automotive photo, preserve approved composition. Extremely fine native sharp details on truck, body, tire treads and headlights. NO text, numbers, logos, marks, typography, globe, map, routes, UI, icons or watermark anywhere. Do not draw the interface. Clean photographic background only. Leave the top sky dark navy (#061527) for seamless composition into a CSS sky.

## Histórico dos assets anteriores

Os registros abaixo descrevem revisões anteriores. A página atual usa os
assets da Issue #409 descritos acima. Os arquivos antigos foram preservados.

CONFIRMADO: `login-logistics-hero-v2.webp` é uma imagem própria gerada com a ferramenta integrada `imagegen`, em 25/10/2026, para substituir a ilustração rejeitada pelo responsável na Issue #306. Não representa uma instalação ou frota real do LoadX.

CONFIRMADO: nenhum arquivo de terceiros foi incorporado. A pesquisa de referências de centros de distribuição consultou a [publicação institucional da DHL](https://www.dhl.com/us-en/home/press/press-archive/2023/dhl-opens-a-silver-leed-certified-distribution-center-in-chicago.html); a imagem gerada não usa marcas, textos, fotografias ou logotipos dessa publicação.

CONFIRMADO: arquivo servido pelo próprio frontend, 1024 × 1536 px, WebP de 162.514 bytes, convertido do PNG gerado com qualidade 86. Não requer serviço externo, biblioteca adicional ou chamada de geração em produção. O componente marca a imagem como decorativa e prioriza seu carregamento. A animação CSS pode ser pausada e respeita movimento reduzido.

## Prompt final

Modo: ferramenta integrada, geração de imagem nova, fundo opaco.

> Create a premium photographic website hero image for a sophisticated logistics management software. Portrait 2:3 composition, editorial architectural commercial photography, absolutely photorealistic. A pristine unbranded modern white European cab-over semi truck with long white box trailer at a contemporary dark steel distribution center at blue hour. Truck in lower half of frame, front three-quarter view, truck front faces toward bottom right, physically correct wheels and cab, elegantly lit with warm amber loading-bay light and subtle cool navy ambient light. Strong perspective lines of warehouse facade, restrained cinematic atmosphere, beautifully realistic materials and asphalt, high-end automotive advertising art direction, calm and confident rather than busy. Top 45 percent mostly dark navy warehouse architecture and evening negative space where the website overlays its own white headline. Lower truck must remain clearly readable, do not make whole image too dark. No text, no logos, no visible license plate text, no watermarks, no humans, no diagrams, no cartoon, no isometric illustration, no UI overlays, no neon cyberpunk effects. One coherent photographic scene. Subtle natural film grain, clean commercial finish.


## Cenário aprovado para o redesign premium — 12/11/2026

`login-cinematic-scene.webp` (900×1000 px, 43.542 bytes, WebP) é um asset próprio da apresentação LoadX, composto a partir da referência visual gerada por IA e aprovada pelo responsável. A composição contém caminhão fictício com marca LoadX, docas, empilhadeira, carga e mapa luminoso da América do Sul. Não retrata clientes, frotas ou instalações reais.

A imagem foi recortada e adaptada para conter **apenas o cenário decorativo**, sem campos de login, botões ou títulos: os textos e a autenticação são renderizados separadamente por React para legibilidade, responsividade, acessibilidade e atualização. Os sinais de rotas, pontos e luzes móveis são camadas SVG/CSS sobre o arquivo e podem ser pausados. Não há requisições a serviços de imagem nem dependências externas.

A imagem antiga `login-logistics-hero-v2.webp` permanece versionada como referência anterior/fallback para eventual reversão; a página de login corrente utiliza o novo arquivo.
