# OC86 — Evidências visuais e funcionais

`CONFIRMADO`: Chromium headless com API FastAPI e PostgreSQL 16 locais reais,
banco exclusivo e dados fictícios. Sessão ADMIN, sem respostas HTTP interceptadas.
Vinte capturas: lista e criação nos temas forçados claro/escuro em larguras
375, 768, 1280 e 1920 px; confirmação sensível, erro do último ADMIN, formulário
DRIVER e registros em mobile. Sem overflow horizontal ou exceção JavaScript.

`CONFIRMADO`: `resultados.json` registra criação e persistência após F5,
vínculo de motorista, ativação/desativação e redefinição administrativa de senha.
Login com a senha nova foi validado; sessão anterior à mudança de perfil/vínculo
passou a retornar 401. Tentativa de desativar o único ADMIN recebeu o erro real,
preservando sua sessão. Nenhuma credencial é mostrada nas capturas ou resultados.

`CONFIRMADO`: modo Automático acompanhou alterações do sistema; modos forçados
foram capturados com o sistema em aparência oposta. Shift+Tab/Tab mantiveram
foco no modal; Escape fechou e devolveu foco ao botão de origem. LocalStorage
contém somente preferências existentes de tema/sidebar, sem dados de usuários.
Capturas de desktop e mobile foram revisadas, incluindo formulário e lista.

`CONFIRMADO`: RBAC dos outros perfis e erros de domínio são cobertos pelos testes
de API/PostgreSQL e componente; não se afirma sessão desses perfis no Chromium.
Evidências locais não representam medição ou publicação em produção. Sem deploy.
