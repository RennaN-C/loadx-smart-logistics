# OC112 — Evidências reais

`CONFIRMADO`: Chromium headless, API FastAPI e PostgreSQL 16 locais reais,
sem respostas interceptadas ou dados pessoais reais. Vinte e duas capturas:
lista/editor em 375, 768, 1280 e 1920 px nos temas claro/escuro; confirmação,
reservadas, associação OC86, perfil em uso, acesso limitado e administração negada.

`CONFIRMADO`: criação/edição de perfil, persistência após F5, criação de conta
CUSTOM associada, login dessa conta com somente trucks.read, ausência de gestão
na frota, 403 real para produtos/usuários/perfis e negação de Configurações.
`resultados.json` registra estados/UUIDs de fixtures, nunca credenciais.

`CONFIRMADO`: modo Automático acompanha sistema, modos forçados capturados com
sistema oposto. Sem overflow horizontal ou exceção JS. Tab/Shift+Tab ficam no
modal, Escape devolve foco à origem; confirmação foca a primeira ação e revisão
retorna ao nome. Capturas de editor/lista em desktop/mobile revisadas; campos
sem estilo e contador quebrado identificados e corrigidos durante a revisão.
LocalStorage somente com preferências de tema/sidebar, sem grants ou credenciais.

`CONFIRMADO`: revogação, concorrência, rollback e demais perfis fixos são cobertos
por API/PostgreSQL/componentes; não se afirma execução de todos no Chromium.
Evidências locais não representam deploy ou medição em produção.
