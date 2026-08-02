# Autenticação

Login, hash de senha, token e autorização por perfil. Não cadastra regras específicas dos demais módulos.

## Estrutura

- `schemas.py`: contratos Pydantic `AuthLogin` e `TokenRead`.
- `dependencies.py`: usuário autenticado e verificação reutilizável de papéis.
- `bootstrap.py`: comando interativo para criar o primeiro `ADMIN`.
- `service.py`: bootstrap, autenticação, emissão de token e resolução do usuário atual.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `POST /api/v1/auth/login`: valida e-mail/senha e retorna token Bearer.
- `GET /api/v1/auth/me`: retorna o usuário autenticado pelo header `Authorization: Bearer <token>`.

`CONFIRMADO`: `D03` e `ADR-004` removeram `POST /api/v1/auth/register` do contrato. O primeiro `ADMIN` usa bootstrap local e os usuários seguintes são criados por `ADMIN` em `/api/v1/users`.

`CONFIRMADO`: a `OC51-D` removeu `/auth/register` também do código e do OpenAPI.

## Regras implementadas

- Senha nunca é retornada pela API.
- Senha é persistida somente como `password_hash`.
- Token JWT usa `sub` com o UUID do usuário.
- Login de usuário inativo é bloqueado.
- `/auth/me` rejeita token ausente, inválido, expirado ou de usuário inexistente.
- `/auth/me` usa o esquema Bearer documentado no OpenAPI.
- Papéis inválidos na configuração da autorização são rejeitados e acesso sem papel permitido usa `AUTH_FORBIDDEN`.
- O bootstrap fixa `role = ADMIN` e `active = true`, lê a senha de forma oculta e recusa execução quando já existe qualquer usuário.

## Pendências

- `CONFIRMADO`: a matriz de permissões e a negação por padrão seguem `docs/04-regras-negocio.md` e `ADR-004`; a `OC51-I` auditou todos os endpoints de negócio implementados.
- `PENDENTE DE DEFINIÇÃO`: política final de expiração, refresh token e bloqueio por tentativas inválidas.
