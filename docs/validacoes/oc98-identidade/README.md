# OC98 — evidências de identidade standalone

`CONFIRMADO`: Chromium headless com frontend Vite, API FastAPI e PostgreSQL 16
isolado `loadx_oc98_browser`, migrations reais. Todos os dados são fictícios.
Entrega de recuperação usa adapter fake exclusivo no processo de validação:
nenhum e-mail real foi enviado. Não se trata de validação de SMTP em produção.

`CONFIRMADO`: 49 capturas em 375/768/1280/1920 px, com prefers-color-scheme claro
e escuro. Amostra versionada por fluxo; matriz em results.json. Capturas foram
revisadas para leitura, alinhamento, foco, botões e ausência de rolagem horizontal.
Códigos aleatórios da fixture foram borrados na captura; não há segredo real.

Fluxos: solicitar recuperação → reset pelo link → remoção do fragmento → senha
nova → login ADMIN → cadastro obrigatório TOTP → negação /auth/me antes de MFA →
comprovação de posse → códigos de recuperação → Meu perfil → F5 restaurando
sessão → novo login com MFA → erro de fator inválido → código de recuperação
aceito. Gerenciamento/revogação/concorrência são também cobertos por testes de
API e PostgreSQL. Não há Web Storage de credenciais ou bypass administrativo.

`RISCO IDENTIFICADO`: entrega SMTP real, domínio/TLS público, NTP, cofre e rotação
de chave, retenção dos eventos e contingência assistida exigem infraestrutura.
Adapter SMTP possui teste de contrato com transporte fake verificando TLS,
timeout e fragmento. ADR-038 e README auth descrevem configuração e limites.
