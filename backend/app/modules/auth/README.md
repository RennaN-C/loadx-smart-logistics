# Autenticação

Login, hash de senha, token e autorização por perfil. Não cadastra regras específicas dos demais módulos.

## Estrutura

- `schemas.py`: contratos Pydantic `AuthLogin` e `TokenRead`.
- `service.py`: registro, autenticação, emissão de token e resolução do usuário atual.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `POST /api/v1/auth/register`: cria usuário interno e retorna os dados públicos.
- `POST /api/v1/auth/login`: valida e-mail/senha e retorna token Bearer.
- `GET /api/v1/auth/me`: retorna o usuário autenticado pelo header `Authorization: Bearer <token>`.

## Regras implementadas

- Senha nunca é retornada pela API.
- Senha é persistida somente como `password_hash`.
- Token JWT usa `sub` com o UUID do usuário.
- Login de usuário inativo é bloqueado.
- `/auth/me` rejeita token ausente, inválido, expirado ou de usuário inexistente.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: matriz final de permissões por perfil.
- `PENDENTE DE DEFINIÇÃO`: política final de expiração, refresh token e bloqueio por tentativas inválidas.
- `SUPOSIÇÃO TÉCNICA`: `POST /auth/register` permanece aberto no MVP local até a equipe decidir se usuários serão criados apenas por administrador.
