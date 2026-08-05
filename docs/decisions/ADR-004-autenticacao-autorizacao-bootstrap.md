# ADR-004: autenticação, autorização e bootstrap administrativo

Status: aceita

## Contexto

O backend possui autenticação JWT, mas os cadastros ainda aceitam acesso anônimo e `POST /api/v1/auth/register` permite criar usuários com papel informado pelo cliente. A `OC51` precisa de uma fronteira pública, uma matriz de permissões e um processo seguro para criar o primeiro administrador.

## Decisão

- Somente `GET /health` e `POST /api/v1/auth/login` são públicos.
- Todos os demais endpoints de negócio exigem autenticação Bearer e consultam o usuário, seu papel e seu estado no banco.
- A autorização aplica menor privilégio e negação por padrão conforme a matriz de `docs/04-regras-negocio.md`.
- Token ausente ou inválido usa `401 AUTH_INVALID_TOKEN`; usuário autenticado sem permissão usa `403 AUTH_FORBIDDEN`.
- O primeiro `ADMIN` é criado por comando administrativo local, somente quando não existem usuários e antes da exposição da API.
- Depois do bootstrap, somente `ADMIN` cria usuários por `POST /api/v1/users`.
- `POST /api/v1/auth/register` é removido.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado.
- Acesso baseado em vínculo, como a própria viagem do `DRIVER`, permanece negado enquanto o relacionamento necessário não existir no modelo aprovado.

## Consequências

- A `OC51` deve proteger todas as rotas existentes, atualizar OpenAPI e adicionar testes por perfil.
- O frontend deve autenticar, enviar Bearer token e tratar `401` e `403`.
- A remoção de `/auth/register` é uma alteração intencional de contrato.
- O bootstrap não usa endpoint HTTP, seed com credencial real nem senha exposta em argumento ou log.
- Duração do token, refresh token, bloqueio de login e recuperação de senha continuam pendentes em `D18`.
