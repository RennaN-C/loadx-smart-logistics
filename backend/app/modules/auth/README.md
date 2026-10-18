# Autenticação

Login, hash de senha, token e autorização por perfil. Não cadastra regras específicas dos demais módulos.

## Estrutura

- `models.py`: sessões opacas e throttling durável de login.
- `schemas.py`: contrato Pydantic `AuthLogin`.
- `repository.py`: persistência de sessões e contadores de login.
- `sessions.py`: emissão, resolução, expiração, CSRF e revogação de sessões.
- `dependencies.py`: sessão autenticada, CSRF e verificação de papéis.
- `bootstrap.py`: comando interativo para criar o primeiro `ADMIN`.
- `service.py`: bootstrap e autenticação.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `POST /api/v1/auth/login`: valida e-mail/senha, cria sessão e retorna o usuário.
- `GET /api/v1/auth/me`: restaura o usuário pelo cookie de sessão.
- `POST /api/v1/auth/logout`: revoga a sessão atual e remove o cookie.

`CONFIRMADO`: `D03` e `ADR-004` removeram `POST /api/v1/auth/register` do contrato. O primeiro `ADMIN` usa bootstrap local e os usuários seguintes são criados por `ADMIN` em `/api/v1/users`.

`CONFIRMADO`: a `OC51-D` removeu `/auth/register` também do código e do OpenAPI.

## Regras implementadas

- Senha nunca é retornada pela API.
- Senha é persistida somente como `password_hash`.
- Sessão usa identificador opaco de 256 bits e persiste somente seu SHA-256.
- Produção usa `__Host-loadx_session` com `HttpOnly`, `Secure`, `SameSite=Lax`,
  `Path=/` e sem `Domain`; local HTTP usa `loadx_session` sem `Secure`.
- Sessões expiram após 30 minutos inativas ou 8 horas absolutas.
- Métodos inseguros exigem origem exata e `X-CSRF-Token` quando autenticados.
- Login de usuário inativo é bloqueado.
- Login não diferencia publicamente e-mail inexistente, senha inválida ou usuário
  inativo.
- Falhas de login são limitadas por conta e IP com HMAC dos identificadores,
  bloqueios progressivos de 1, 5, 15 e 60 minutos e `Retry-After`.
- Uma autenticação válida remove os contadores correspondentes; não existe
  bloqueio permanente automático.
- Login, falha, criação, expiração e revogação de sessão emitem eventos JSON no
  logger `loadx.security`. Falhas contra papel crítico ou com atraso de
  throttling usam `alert=true`; os eventos não aceitam e-mail, IP bruto, senha,
  segredo, documento ou token.
- `/auth/me` rejeita sessão ausente, inválida, revogada, expirada ou de usuário
  inexistente.
- O OpenAPI documenta o esquema cookie `SessionCookie`.
- Papéis inválidos na configuração da autorização são rejeitados e acesso sem papel permitido usa `AUTH_FORBIDDEN`.
- O bootstrap fixa `role = ADMIN` e `active = true`, lê a senha de forma oculta e recusa execução quando já existe qualquer usuário.

## Pendências

- `CONFIRMADO`: a matriz de permissões e a negação por padrão seguem `docs/04-regras-negocio.md` e `ADR-004`; a `OC51-I` auditou todos os endpoints de negócio implementados.
- `CONFIRMADO`: D18 e `ADR-020` eliminaram JWT/refresh token para o frontend
  próprio e definiram sessões opacas revogáveis.


## Minha conta — OC92

`CONFIRMADO`: todos os perfis autenticados podem consultar `/auth/me` e usar os contratos próprios abaixo. O ator sempre vem da sessão; não existe parâmetro de usuário alvo.

| Método e caminho (prefixo `/api/v1`) | Contrato |
|---|---|
| `PATCH /auth/me` | Nome e e-mail obrigatórios, normalizados; somente esses dois campos são aceitos. Retorna `UserRead`, sem credenciais. |
| `POST /auth/me/password` | `current_password`, `new_password`; política central de 15–128 caracteres/Unicode/blocklist. Sucesso 204, revoga **todas** as sessões, inclusive atual, e remove cookie. Novo login obrigatório. |
| `GET /auth/me/sessions` | Array das sessões próprias não revogadas e não expiradas. UUID, `current`, `created_at`, `last_seen_at`, `idle_expires_at`, `absolute_expires_at`; sem token/hash, IP ou user agent. |
| `DELETE /auth/me/sessions/{session_id}` | 204 para sessão própria (idempotente enquanto autenticado); 404 indistinguível para UUID inexistente ou de outro usuário. Remove cookie se a atual for revogada. |
| `POST /auth/me/sessions/revoke-others` | 204; revoga as demais sessões e mantém a atual. |

`CONFIRMADO`: campos extras como role/active/password/driver_id em edição pessoal retornam 422; e-mail duplicado retorna 409. Senha atual incorreta retorna 400 `AUTH_CURRENT_PASSWORD_INVALID`, sem revogar a sessão. Falhas de confirmação usam o throttling durável existente por conta/IP, com 429/Retry-After quando bloqueado. Validar a política da nova senha não emite sessão ou modifica dados.

`CONFIRMADO`: métodos inseguros preservam Origin e CSRF centrais; ausência/expiração/revogação usam 401 e usuário inativo 403. Alterações pessoais reutilizam `UserService`, unicidade PostgreSQL e auditoria `USER_UPDATED` com nomes dos campos, sem valores. Eventos `AUTH_OWN_PROFILE_UPDATED`, `AUTH_OWN_PASSWORD_CHANGED`, `AUTH_OWN_PASSWORD_REJECTED` e revogação usam somente UUIDs/metadados seguros.

`CONFIRMADO`: mutações bloqueiam usuário antes de sessões e revalidam a sessão sob lock. Consulta autenticada segue a mesma ordem para evitar deadlocks. Troca de hash, revogação e auditoria compartilham commit/rollback. A emissão ao final do login compara o hash verificado com o atual sob lock de usuário, impedindo criar uma sessão com credenciais invalidadas por troca concorrente. Nenhuma migration: `users`, `auth_sessions` e `audit_events` atuais suportam o contrato; head `20261009_0023`.

`CONFIRMADO`: frontend restaura os dados por `/auth/me` após F5; lista sessões pela API, oferece confirmação e reconsulta após revogação. Não grava dados de sessão em Web Storage nem inventa dispositivos/localização. Conta é separada de configurações administrativas e logísticas. Password/sessions ficam concentrados no módulo auth e nos adapters da feature de conta, para futura delegação central, sem SSO, MFA, recuperação ou administração de terceiros nesta OC.

## OC98 — recuperação de senha e MFA

`CONFIRMADO`: ADR-038 complementa ADR-020. Login de ADMIN/LOGISTICS_MANAGER (ou
conta com MFA voluntário) retorna `MfaChallengeRead` em vez de `UserRead`:
`challenge_token`, `purpose=ENROLL|LOGIN`, `expires_at`. Nenhum cookie autenticado
é emitido antes de `POST /auth/mfa/verify`. Login CHECKER/DRIVER sem MFA preserva
UserRead/cookie/CSRF. Consumidores devem discriminar pela presença de
`challenge_token`; frontend mantém a credencial intermediária somente em memória.

| Método/caminho | Entrada / retorno |
|---|---|
| POST /auth/password-recovery | email / 202 neutro; 503 se infraestrutura ausente para qualquer conta |
| POST /auth/password-recovery/confirm | token, new_password / 204, encerra todas as sessões, sem login automático |
| POST /auth/mfa/setup | challenge_token ENROLL / provisioning_uri, somente configuração autorizada |
| POST /auth/mfa/verify | challenge_token, code (TOTP ou recuperação em LOGIN) / user, recovery_codes; cookie/CSRF normal somente após validação |
| GET /auth/me/mfa | sessão própria / enabled, required; nunca segredo ou códigos |
| POST /auth/me/mfa/enroll | password / desafio ENROLL, revoga sessões anteriores; somente conta ainda sem MFA |
| POST /auth/me/mfa/recovery-codes | password, code / códigos novos, anteriores invalidados |
| POST /auth/me/mfa/disable | password, code / 204, revoga todas as sessões; perfil sensível exige novo cadastro no login |

Todos os caminhos usam `/api/v1`. Endpoints intermediários exigem Origin e
credencial restrita; os de conta preservam também cookie/CSRF e ownership. 400
indica verificação inválida/expirada, 429 orçamento durável excedido, 503 chave
ou infraestrutura indisponível. Schemas extras são proibidos. Edição de e-mail
em conta com MFA exige `current_password` + `second_factor`, invalida links
pendentes e consome segundo fator na transação da edição. ADMIN não possui
reset de MFA de terceiros.

Tokens usam SHA-256 e alta entropia; códigos TOTP não são persistidos. Segredo
TOTP é cifrado com Fernet; `cryptography` é a única dependência nova, justificada
pela criptografia autenticada. RFC 6238 testada com vetores oficiais. A mesma
ordem de locks de OC92 serializa consumo/replay/revogação. Falha de auditoria
reverte hash, token, fator e sessão. Migration 20261018_0025 sucede 20261016_0024 (OC112) e revoga
sessões sensíveis anteriores; downgrade bloqueia dados OC98, sem apagá-los.

### Configuração de produção

- MFA_ENCRYPTION_KEY: chave Fernet independente, via cofre/secrets; nunca usar
  SECRET_KEY nem chave de teste. Provisionar antes de aplicar OC98.
- PASSWORD_RECOVERY_PROVIDER=smtp, PASSWORD_RECOVERY_URL=https://dominio-aprovado/password-reset.
- SMTP_HOST, SMTP_PORT (465 por padrão), SMTP_USERNAME, SMTP_PASSWORD e SMTP_SENDER.
- SMTP usa TLS verificado, autenticação e timeout de cinco segundos. Link usa
  fragmento; o frontend o remove do histórico imediatamente após montagem.
- Sem configuração, falha fechada e não afirma entrega. 202 aceita solicitação,
  não comprova recebimento SMTP. BackgroundTasks separa entrega da resposta;
  falha emite somente evento seguro; queda do processo exige reenvio. Não há
  promessa de fila durável ou SLA de e-mail nesta OC.
- Sincronização UTC/NTP, backup/restauração da chave, retenção dos eventos e
  recuperação assistida com duplo controle são responsabilidades operacionais.

`RISCO IDENTIFICADO`: não trocar/perder MFA_ENCRYPTION_KEY sem recriptografar
segredos existentes. Sem dispositivo e códigos, acesso permanece bloqueado;
contingência assistida não possui endpoint de bypass. SMTP real requer
infraestrutura aprovada e não é acionado por testes/fake de navegador.

`CONFIRMADO`: revisão de concorrência revalida o estado MFA/papel no próprio gate
sob lock de conta/fator antes de emitir sessão por senha e conserva o hash
verificado mesmo após commit/expiração ORM. Promoção de perfil, ativação do fator
ou troca de senha concorrentes abortam esse login. Ativação invalida sessões por
senha criadas durante cadastro voluntário. Consumo de código de recuperação é
registrado somente depois do commit, inclusive na edição de e-mail. Limites de
login só são limpos após comprovar o segundo fator. Testes específicos cobrem
essas janelas e a ausência de evento de consumo em rollback.
