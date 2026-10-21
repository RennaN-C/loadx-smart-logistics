# Dispositivo confiável — Issue #222

`CONFIRMADO`: Chromium real, backend local e PostgreSQL 16 em banco isolado
`loadx_issue222_browser`, com dados fictícios e flag de confiança habilitada
somente no processo de validação. Nenhum banco legado, `.env` ou chave MFA do
usuário foi alterado. Não houve deploy.

Validado em 375/768/1280/1920 px, temas claro/escuro, sem rolagem horizontal:

- Primeiro cadastro ENROLL preserva QR e dez códigos, sem opção de confiança.
- LOGIN oferece checkbox desmarcado; seleção por teclado Espaço e TOTP real.
- Login por senha depois de logout dispensa o fator no navegador confiável.
- Sessão expirada no banco exclusivo retorna 401; novo login exige senha e usa
  confiança, sem estender a sessão anterior ou recriar fator.
- Outra sessão isolada de navegador exige MFA para a mesma conta.
- Meu perfil lista este navegador, último uso e expiração; esquecer remove
  confiança, preserva sessão atual e volta a exigir MFA no próximo login.

As oito capturas mostram apenas login sem código e a seção de dispositivos,
em mobile e desktop, sem tokens, QR, senhas ou códigos de recuperação.
Dados/horários são exemplos fictícios do navegador de testes (UTC); a aplicação
formata datas de acordo com o fuso do navegador do usuário.

`RISCO IDENTIFICADO`: testes de navegador não substituem aceite manual em
homologação, configuração segura da flag, TLS e custódia da chave. A confiança
não vincula hardware; cookie roubado com senha é risco até expiração/revogação.
Resultados completos de lint/testes/coverage/CI ficam na PR #211.
