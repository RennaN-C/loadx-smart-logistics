# OC112 — Gestão unificada de usuários e perfis

`CONFIRMADO`: 35 capturas reais do Chromium 151 com API FastAPI e PostgreSQL 16
locais isolados; sem interceptação de respostas, imagens simuladas ou dados
pessoais reais. Usuários/perfis de exemplo são fixtures fictícias. Nenhuma senha,
cookie ou token é registrado nas imagens ou em resultados.json.

## Comparação e telas finais

- [Antes: perfis separados](../oc112/perfis-1280-dark.png).
- [Depois: perfis na Gestão de usuários](perfis-1280-dark.png).
- [Usuários — desktop](usuarios-1280-dark.png), [tablet claro](usuarios-768-light.png).
- [Atribuição com resumo — mobile](atribuicao-375-dark.png).
- [Editor compacto — desktop](editor-1280-dark.png), [mobile claro](editor-375-light.png).
- [Consulta protegida e rótulos legíveis](consulta-protegido-1280-dark.png).
- [Confirmação de alteração](confirmacao-1280-dark.png).
- [Foco após o atalho de gerenciamento](atalho-foco-1280-dark.png).

`CONFIRMADO`: usuários, perfis, atribuição e edição capturados em 375, 768, 1280
e 1920 px nos temas claro/escuro (32 imagens), mais consulta, confirmação e foco do atalho. A
captura de atribuição mostra a seção Acesso e permissões no formulário rolado;
o editor usa somente a rolagem externa do modal. Rodapé alcançável em todas as
larguras; sem overflow horizontal. Temas forçados com sistema oposto.

`CONFIRMADO`: revisão encontrou e corrigiu a herança de largura de inputs nos
rádios; controles ficaram em 18 px, com verificação de largura máxima de 20 px.
Hierarquia, legibilidade, densidade, foco e ações revisados nas capturas, além
das verificações automatizadas. O cabeçalho da área é Gestão de usuários, sem
repetição visual de títulos. Capturas anteriores à correção foram substituídas.

## Fluxos exercitados no navegador

`CONFIRMADO`: login ADMIN; link antigo; criação de perfil, confirmação e
associação na criação de usuário; nome real na listagem; F5 com dados
persistidos; atalho para gerenciar perfis e retorno com campos preservados e
senha limpa; teclado nas abas; Enter no atalho leva o foco à aba de perfis e voltar por seta
restaura o foco no nome do formulário, preservando o rascunho e limpando a senha;
perfis fixos somente consulta; reservadas
desabilitadas; perfil em uso não pode ser inativado.

`CONFIRMADO`: login CUSTOM em contexto separado, projeção efetiva real e 403
na API/negação da tela administrativa. Alteração de grants pela UI revogou a
sessão existente (auth/me 401); novo login recebeu os grants atuais. Gestor,
conferente e motorista receberam negação administrativa e 403 na API de usuários.
Sem exceções de JavaScript. resultados.json contém somente os resultados e UUID
da fixture, nunca credenciais.

`CONFIRMADO`: teste de edição alterou a seleção da fixture de duas permissões
para uma após as primeiras capturas. As imagens finais foram refeitas com o
estado persistido atual. Versão/conflito, rollback e último ADMIN são cobertos
pelas regressões de backend e componentes; não se afirma execução de todos os
casos no navegador. Nenhum merge, deploy ou integração externa foi executado.
