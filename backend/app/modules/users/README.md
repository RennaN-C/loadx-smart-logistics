# Usuários

`CONFIRMADO`: `get_user_for_authorization` é a leitura pública sob lock SHARE
usada pela OC79; atualiza entidades já carregadas e mantém papel/atividade/vínculo
estáveis até terminar a transação externa. Não recebe role/permissões do cliente.

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
  `created_at`, `email`, `driver_id` e `driver_name` (nullable), conforme OC86/ADR-017.
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

## OC86 — Gestão de contas pelo ADMIN

`CONFIRMADO`: GET da coleção aceita `search` opcional somente por nome
(semântica literal da OC95), `role` do catálogo fixo e `active` booleano,
combinados por AND antes de COUNT/LIMIT/OFFSET. Ordenação created_at/id e
envelope existentes preservados. A lista ADMIN-only inclui e-mail e vínculo;
nomes dos motoristas vêm de projeção pública do DriverService em uma consulta
limitada aos IDs da página, sem N+1 nem dados de documento/telefone/CNH.

`CONFIRMADO`: frontend em Configurações → Gestão de usuários reutiliza as quatro
rotas existentes. Alterações sensíveis exigem confirmação; PATCH envia somente
campos alterados. Não há DELETE, novas permissões, tenant ou autenticação paralela.
Senha fica somente na memória do formulário, é limpa após resposta/fechamento e
não aparece na confirmação, listagem, logs ou auditoria. Último ADMIN e unicidade
continuam validados transacionalmente no backend.

`CONFIRMADO`: DRIVER sem vínculo continua permitido pelo contrato standalone;
a UI esclarece que viagens próprias exigem vínculo ativo. Motorista arquivado
pode continuar identificado no vínculo sem liberar elegibilidade operacional.
A criação/edição de identidade permanece isolada do domínio logístico, por UUID.
Nenhuma integração CoreFlow, recuperação, MFA ou OC112 é antecipada.
