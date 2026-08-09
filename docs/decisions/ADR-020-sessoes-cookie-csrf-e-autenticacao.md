# ADR-020: sessões opacas, cookie seguro e política final de autenticação

Status: aceita

## Contexto

O LoadX usava JWT Bearer persistido pelo frontend em `localStorage`. Esse modelo
mantinha uma credencial reutilizável acessível a JavaScript e não oferecia
revogação imediata no logout, na troca de senha ou na desativação do usuário.
A D18 também mantinha pendentes a duração da autenticação, a limitação de login
e a política definitiva de senha.

`CONFIRMADO`: o LoadX será consumido somente pelo frontend próprio nesta etapa.
Não existem clientes externos que precisem preservar o contrato Bearer.

## Decisão

- O JWT Bearer é substituído por sessão opaca revogável no backend. Não existe
  refresh token no MVP.
- Cada login gera pelo menos 256 bits aleatórios. Somente o SHA-256 do
  identificador é persistido em `auth_sessions`.
- Em produção, o identificador usa o cookie `__Host-loadx_session`, com
  `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` e sem `Domain`. O ambiente local
  HTTP usa `loadx_session`, sem o prefixo reservado nem `Secure`.
- A sessão expira após 30 minutos de inatividade ou 8 horas absolutas. O menor
  prazo sempre prevalece.
- `POST /auth/logout` revoga a sessão atual e remove o cookie. Troca de senha,
  desativação ou alteração de papel revogam todas as sessões do usuário na mesma
  transação.
- Requisições `POST`, `PUT`, `PATCH` e `DELETE` exigem `Origin` presente em
  `BACKEND_CORS_ORIGINS`. Rotas autenticadas com esses métodos também exigem um
  token sincronizador associado à sessão no header `X-CSRF-Token`.
- CORS usa lista exata, credenciais habilitadas e expõe somente o header de CSRF
  necessário ao frontend.
- Login é limitado por conta e por IP. As quatro primeiras falhas não bloqueiam;
  da quinta em diante os intervalos são 1, 5, 15 e 60 minutos. O maior bloqueio
  aplicável prevalece, `429` inclui `Retry-After` e uma autenticação válida zera
  os dois contadores.
- E-mail inexistente, senha inválida e usuário inativo retornam a mesma resposta
  pública de credenciais inválidas. Identificadores usados no throttling são
  persistidos somente como HMAC-SHA-256.
- Novas senhas e trocas exigem de 15 a 128 caracteres, aceitam espaços e Unicode,
  não aplicam regra de composição e consultam uma blocklist local de senhas
  comuns e termos esperados do produto.
- Novos hashes usam Argon2id com memória de 19 MiB, duas iterações e paralelismo
  1. Um hash PBKDF2 legado continua verificável e é atualizado para Argon2id
  após login válido.

## Consequências

- As decisões Bearer/JWT da `ADR-004` e os limites JWT da `ADR-019` são
  substituídos por esta ADR; RBAC, bootstrap e fronteira pública permanecem.
- O frontend usa `withCredentials`, mantém o token CSRF somente em memória e não
  persiste credencial de autenticação em Web Storage.
- A aplicação consulta usuário, papel e estado no banco em cada requisição e
  pode revogar sessões individualmente ou por usuário.
- `auth_sessions` e `auth_login_throttles` passam a integrar o modelo oficial e
  são criadas exclusivamente por migration Alembic.
- `RISCO IDENTIFICADO`: TLS, HSTS no proxy, cofre de segredos, alertas externos e
  segregação dos papéis PostgreSQL pertencem ao ambiente de implantação e não
  são resolvidos somente pelo código da aplicação.
- `PENDENTE DE DEFINIÇÃO`: recuperação de senha e resposta a comprometimento
  precisam de fluxo operacional próprio.
- `PENDENTE DE DEFINIÇÃO`: MFA para `ADMIN` e `LOGISTICS_MANAGER` será uma
  ocorrência separada após definir cadastro de passkey, fallback TOTP,
  recuperação e bootstrap sem bloqueio administrativo.

## Referências de segurança

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html).
