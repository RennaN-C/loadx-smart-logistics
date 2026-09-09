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
