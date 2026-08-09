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

`CONFIRMADO`: a `OC51-D` aplicou a proteção no router; a OC60 substituiu Bearer
pelo esquema cookie `SessionCookie` no OpenAPI.

## Regras implementadas

- `email` é normalizado para minúsculas.
- `email` deve ser único.
- `role` é normalizado para maiúsculas.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `driver_id` é opcional, único e referencia `drivers.id` com exclusão restrita.
- `driver_id` preenchido exige papel `DRIVER` e motorista existente; o mesmo
  motorista não pode pertencer a dois usuários.
- Novas senhas e trocas exigem de 15 a 128 caracteres, aceitam espaços e
  Unicode, não usam regra de composição e consultam a blocklist local da D18.
- A blocklist interna cobre valores comuns e derivados do contexto LoadX. Uma
  lista adicional aprovada pela operação pode ser montada como arquivo UTF-8 e
  informada em `PASSWORD_BLOCKLIST_PATH`; ela é carregada uma vez por processo,
  limitada a 5 MiB e 100.000 valores e nunca depende de consulta externa durante
  criação ou troca de senha.
- A comparação usa a senha inteira normalizada em NFC e sem diferenciar caixa;
  uma frase forte não é rejeitada apenas por conter uma palavra isolada da lista.
- Novos hashes usam Argon2id com m=19 MiB, t=2 e p=1.
- Hashes PBKDF2 legados continuam verificáveis e são migrados para Argon2id após
  um login válido.
- Troca de senha, desativação e alteração de papel revogam todas as sessões do
  usuário na mesma transação da atualização.
- Alteração ou remoção de `driver_id` também revoga todas as sessões na mesma
  transação.
- Mudanças de senha, papel ou estado emitem `AUTH_USER_SECURITY_STATE_CHANGED`;
  alteração de papel e desativação são marcadas com `alert=true`.
- `password_hash` nunca é retornado pela API.
- `active = false` bloqueia login.
- O último `ADMIN` ativo não pode ser desativado ou rebaixado.
- A verificação do último administrador bloqueia os administradores ativos durante a transação para evitar alterações concorrentes incompatíveis.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: recuperação de senha pertence a uma ocorrência
  futura.
