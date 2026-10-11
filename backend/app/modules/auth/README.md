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
