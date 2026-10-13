# Feature: auth

Login, sessão e proteção de rotas.

## Estrutura

- `pages/LoginPage.tsx` (+ `LoginPage.css`): tela de login (`OC24`), painel de marca e formulário.
- `components/AuthProvider.tsx`: contexto de sessão (`loading`/`authenticated`/`unauthenticated`), restauração ao montar e reação a sessão invalidada (`AUTH_INVALID_TOKEN`/`AUTH_USER_INACTIVE`).
- `components/AuthContext.ts`: o Context em si, separado do provider para preservar o Fast Refresh.
- `components/RequireAuth.tsx`: guarda de rota, redireciona para `/login` quando não autenticado.
- `components/SessionLoading.tsx`: estado de carregamento compartilhado por `RequireAuth` e `LoginPage`.
- `components/BrandPanel.tsx`: painel estático de marca da tela de login.
- `components/LoginForm.tsx`: formulário controlado de e-mail/senha.
- `components/loginErrorMessages.ts`: tradução dos códigos de erro do backend para texto de interface.
- `api/authApi.ts`: login, restauração e logout revogável.
- `hooks/useAuth.ts`: hook de acesso ao contexto de sessão.
- `types.ts`: `Role`, `AuthenticatedUser`, `AuthStatus`, `AuthContextValue`.

`CONFIRMADO` por D18 e `ADR-020`: o identificador da sessão fica somente no
cookie `HttpOnly`; o frontend não lê nem persiste credenciais. O
`X-CSRF-Token` devolvido por login e `/auth/me` fica apenas em memória em
`frontend/src/services/csrfToken.ts`.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: recuperação de senha e MFA para funções críticas
  pertencem a ocorrências futuras.


## OC92 — Meu perfil

`CONFIRMADO`: `/account` fica dentro de RequireAuth/AppLayout para ADMIN, LOGISTICS_MANAGER, CHECKER e DRIVER. Entrada Minha conta → Meu perfil e link contextual em Configurações (ADMIN); retorno ao início disponível. Não modifica a proteção de `/settings` nem as seções OC91/OC108.

`CONFIRMADO`: `accountApi.ts` concentra contratos próprios de edição, senha e sessões. `OwnProfileForm`, `OwnPasswordForm` e `OwnSessionsPanel` isolam estados de carregamento, envio, validação, falha parcial, vazio e confirmação. Metadata vem da API; sem armazenamento local, localização ou dispositivo fictício. Senhas têm controles acessíveis de visibilidade e confirmação; o backend valida política/CSRF/ownership.

`CONFIRMADO`: atualização bem-sucedida sincroniza o usuário no AuthProvider. Troca de senha ou encerramento da atual limpa CSRF/estado autenticado pelo contexto central e exige login; mensagem de sucesso permanece somente em memória. Expiração e revogação remotas preservam a reação central existente. Revogar outra sessão reconsulta a lista. Falha transitória conserva a lista anterior com aviso explícito; não declara revogação concluída quando a API falha.

`CONFIRMADO`: a conta standalone é visualmente separada de preferências logísticas futuras. Sem OC86/OC98/OC112, MFA/recuperação/SSO ou nova dependência. Layout de uma coluna em telas pequenas e duas em telas largas, controles sem sobreposição e labels ligados aos inputs.

## OC98 — recuperação e MFA

`CONFIRMADO`: /password-recovery solicita link neutro; /password-reset lê token
do fragmento, limpa URL e exige nova senha/confirmar, sem autenticar. Login
recebe desafio ENROLL/LOGIN em memória no AuthProvider e apresenta
MfaChallengePanel. Senha correta não atualiza usuário autenticado nessa etapa.
Setup exibe URI autorizada, verifica posse e mostra códigos uma vez; confirmação
pelo usuário limpa os códigos. F5 no desafio exige novo login. Depois de concluir,
F5 usa /auth/me e a sessão normal da OC92.

OwnMfaPanel consulta estado real e exige senha + fator para regenerar/trocar;
ativação voluntária encerra a sessão e retorna ao desafio. Nenhum segredo usa
Web Storage. Mudança de e-mail em conta com MFA exige confirmação reforçada.
Origin/CSRF e cliente HTTP existentes permanecem. Telas usam componentes/tokens
locais, temas por prefers-color-scheme, labels e mensagens reais. CoreFlow/SSO
não implementados. Requisitos de infraestrutura e contingência: ADR-038.
