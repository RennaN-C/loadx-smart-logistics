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

- `GET /api/v1/users`: lista usuários.
- `POST /api/v1/users`: cria usuário.
- `GET /api/v1/users/{id}`: consulta usuário por ID.
- `PATCH /api/v1/users/{id}`: atualiza campos enviados.

## Regras implementadas

- `email` é normalizado para minúsculas.
- `email` deve ser único.
- `role` é normalizado para maiúsculas.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `password` deve ter no mínimo 8 caracteres na entrada.
- `password_hash` nunca é retornado pela API.
- `active = false` bloqueia login.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: proteger endpoints de usuários por perfil quando a matriz RBAC for aprovada.
- `PENDENTE DE DEFINIÇÃO`: política de senha definitiva.
