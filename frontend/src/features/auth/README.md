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
- `api/authApi.ts`: `login` (`POST /auth/login`) e `getCurrentUser` (`GET /auth/me`).
- `hooks/useAuth.ts`: hook de acesso ao contexto de sessão.
- `types.ts`: `Role`, `AuthenticatedUser`, `AuthStatus`, `AuthContextValue`.

`frontend/src/services/tokenStorage.ts` (fora desta pasta, compartilhado): `getToken`/`setToken`/`clearToken` sobre `localStorage`. `setToken` valida forma (3 segmentos) e expiração (`exp`) antes de gravar; rejeita com `Error` caso contrário.

## Pendências

- `D18` (duração final do token, refresh token, bloqueio de tentativas, recuperação de senha) segue em aberto — hoje o token é fixo em 60 minutos, sem refresh.
- `DECISÃO NECESSÁRIA`: persistência do token em `localStorage` foi apontada pelo SonarCloud (Security Rating) como hotspot. Mitigado nesta ocorrência com validação de forma/expiração antes de gravar (`tokenStorage.setToken`). A solução ideal — cookie `HttpOnly` — exige mudança de contrato no backend (o login hoje devolve o token no corpo da resposta, não em cookie) e está fora do escopo do frontend; precisa de ADR e decisão conjunta com o time de backend antes de implementar.
