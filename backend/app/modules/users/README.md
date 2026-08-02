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

`CONFIRMADO`: todas essas rotas exigem `ADMIN` conforme `D02`, `D03` e `ADR-004`.

`RISCO IDENTIFICADO`: o router ainda não aplica essa proteção até a implementação da `OC51`.

## Regras implementadas

- `email` é normalizado para minúsculas.
- `email` deve ser único.
- `role` é normalizado para maiúsculas.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `password` deve ter no mínimo 8 caracteres na entrada.
- `password_hash` nunca é retornado pela API.
- `active = false` bloqueia login.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado após a implementação da `OC51`.

## Pendências

- `CONFIRMADO`: proteger os endpoints e o último `ADMIN` ativo faz parte da `OC51`.
- `PENDENTE DE DEFINIÇÃO`: política de senha definitiva.
