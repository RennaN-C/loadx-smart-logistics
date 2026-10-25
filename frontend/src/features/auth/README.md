# Feature: auth

Login, sessão e proteção de rotas.

## Estrutura

- `pages/LoginPage.tsx` (+ `LoginPage.css`): tela de login (`OC24`), painel de marca e formulário.
- `components/AuthProvider.tsx`: contexto de sessão (`loading`/`authenticated`/`unauthenticated`), restauração ao montar e reação a sessão invalidada (`AUTH_INVALID_TOKEN`/`AUTH_USER_INACTIVE`).
- `components/AuthContext.ts`: o Context em si, separado do provider para preservar o Fast Refresh.
- `components/RequireAuth.tsx`: guarda de rota, redireciona para `/login` quando não autenticado.
- `components/SessionLoading.tsx`: estado de carregamento compartilhado por `RequireAuth` e `LoginPage`.
- `components/BrandPanel.tsx`: painel de marca com ilustração decorativa e controle de movimento.
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

- `CONFIRMADO`: recuperação e MFA foram implementados na OC98, descrita abaixo.
  O aceite externo de recuperação permanece no relatório de prontidão da v1.2.0.


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

`CONFIRMADO`: cadastro MFA mostra QR SVG gerado localmente por `qrcode.react`,
com margem branca fixa para leitura em ambos os temas e layout fluido. Chave e
URI manuais ficam em detalhes; clipboard bloqueado permite seleção manual.
Preparação não é repetida por rerender e expiração apaga o provisionamento.
Nenhum segredo vai para serviço de QR, Web Storage ou logs. Leia o
[roteiro SMTP/Mailpit](../../../../backend/app/modules/auth/README.md#complemento-oc98--qr-local-e-transporte-de-e-mail).

`CONFIRMADO`: Issue #222 adiciona opt-in de dispositivo confiável apenas na
etapa LOGIN quando o servidor informa `trusted_device_days`. Checkbox inicia
desmarcado; a explicação distingue TOTP de recuperação e alerta sobre navegador
compartilhado. A API recebe booleano explícito, sem armazenamento de credenciais
no JavaScript. Meu perfil → Segurança apresenta listagem real com datas, estado
vazio/loading/erro, remoção própria e confirmação para revogar todos. Identificação
usa UUID parcial; não inventa nome de hardware. Cookie HttpOnly é controlado
pelo backend. Falhas mantêm a lista e oferecem nova consulta. Temas e layout
responsivo usam tokens atuais; sessões e reautenticação sensível preservadas.


## OC103 — preferências de notificações

`CONFIRMADO`: Meu perfil incorpora NotificationPreferences, com persistência real
por conta via /notifications/preferences. O link da central abre a seção por hash
com foco visual preservado. Aparência, dados, senha e sessões mantêm contratos da
OC92; nenhuma implementação da OC98 isolada é incorporada.


## Retomada de links e acesso mobile — auditoria #256 / #267

`CONFIRMADO`: novos fragmentos de recuperação na mesma aba são consumidos e
removidos da URL, limpando feedback anterior sem salvar tokens em storage.
Respostas anteriores não sobrescrevem outro link. Prazo, uso único, revogação e
MFA continuam definidos pelo backend. F5 não recupera um token apagado da URL.
A marca fica compacta no mobile; o formulário aparece antes da ilustração
(desktop), sem título sobreposto ou rodapé com versão/ambiente inventados.

## Perfil e acesso — revisão visual de 24/10/2026

`CONFIRMADO`: Meu perfil tem abas Dados pessoais, Segurança e MFA, e Sessões e
dispositivos. A seleção usa `/account?tab=data|security|sessions`; valor ausente
ou desconhecido abre Dados pessoais. Painéis permanecem montados para preservar
rascunhos. Aparência e notificações ficam em detalhes expansíveis. Dispositivos
confiáveis acompanham as sessões; MFA e alteração de senha continuam usando os
mesmos contratos e confirmações.

`CONFIRMADO`: login e recuperação compartilham painel de marca. O visual
decorativo não representa resultado do otimizador nem estado operacional.

## Acesso profissional — Issue #304, 25/10/2026

`CONFIRMADO`: LoginPage.css unifica o layout de login/recuperação com painel
navy, formulário no tema escolhido, foco/hover e entrada discreta. BrandPanel
usava LoginIllustration: SVG decorativo com caminhão e volumes, substituído pela
revisão fotográfica da Issue #306 abaixo. Os efeitos contínuos
podem ser pausados pelo botão Pausar efeitos; a preferência de movimento
reduzido desativa animações/transições e oculta o controle desnecessário.

`CONFIRMADO`: formulários, senhas, desafio MFA, recuperação, cookies, CSRF e
redirecionamentos mantêm seus contratos. Nenhum envio externo foi realizado
na verificação visual. Capturas e matriz em
[login profissional](../../../../docs/evidencias/login-profissional/README.md).

## Painel fotográfico — Issue #306, 25/10/2026

`CONFIRMADO`: a ilustração e sua moldura foram removidas. BrandPanel usa uma
imagem própria de aparência fotográfica como fundo, com gradientes para leitura,
etapas discretas no rodapé e zoom lento pausável. Mobile mantém a marca compacta
e o formulário visível. O asset WebP é local, decorativo e tem carregamento
prioritário; não adiciona dependências nem utiliza hotlink.

`CONFIRMADO`: proveniência e prompt em
[images/README.md](../../../public/images/README.md). Capturas e verificações em
[login fotográfico](../../../../docs/evidencias/login-fotografico/README.md).
