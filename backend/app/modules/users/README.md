# Usuários

Cadastro e manutenção de usuários internos e seus papéis.

## Estrutura

- `models.py`: entidade SQLAlchemy `User`.
- `schemas.py`: contratos Pydantic `UserCreate`, `UserUpdate` e `UserRead`.
- `repository.py`: consultas e persistência de usuários.
- `service.py`: regras de e-mail único, hash de senha, criação, consulta e atualização.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/users`: lista paginada com `id`, `name`, `role`, `active` e
  `created_at`; omite `email`.
- `POST /api/v1/users`: cria usuário.
- `GET /api/v1/users/{id}`: consulta usuário por ID.
- `PATCH /api/v1/users/{id}`: atualiza campos enviados.

`CONFIRMADO`: todas essas rotas exigem `ADMIN` conforme `D02`, `D03` e `ADR-004`.

`CONFIRMADO`: a `OC51-D` aplicou a proteção no router e documentou o esquema Bearer no OpenAPI.

## Regras implementadas

- `email` é normalizado para minúsculas.
- `email` deve ser único.
- `role` é normalizado para maiúsculas.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- Novas senhas e trocas exigem de 15 a 128 caracteres, aceitam espaços e
  Unicode, não usam regra de composição e consultam a blocklist local da D18.
- Novos hashes usam Argon2id com m=19 MiB, t=2 e p=1.
- Hashes PBKDF2 legados continuam verificáveis e são migrados para Argon2id após
  um login válido.
- `password_hash` nunca é retornado pela API.
- `active = false` bloqueia login.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado.
- A verificação do último administrador bloqueia os administradores ativos durante a transação para evitar alterações concorrentes incompatíveis.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: recuperação de senha pertence a uma ocorrência
  futura.
