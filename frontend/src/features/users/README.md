# OC86 — Gestão de usuários

`CONFIRMADO`: feature de identidade local standalone, protegida por ADMIN no
frontend e no backend. Client HTTP isolado em usersApi usa GET/POST /users e
GET/PATCH /users/{id}, cookie/CSRF do wrapper existente e DTOs tipados. Não cria
credenciais no domínio logístico nem usa e-mail como identificador técnico.

`CONFIRMADO`: listagem paginada com nome/e-mail/perfil/estado/nome do motorista,
busca por nome e filtros/ordenação no servidor. Falhas, vazio, loading e retry
separados. Nenhuma busca por e-mail/CPF/CNH ou varredura local de registros.
DriverLinkField usa páginas da API de motoristas e detalhe somente do selecionado;
nomes na lista de usuários vêm da projeção batelada do backend.

`CONFIRMADO`: edição consulta o detalhe antes de abrir. PATCH envia somente os
campos alterados. Confirmação para perfil, estado, vínculo e senha não contém
senhas. Role diferente de DRIVER envia remoção explícita do vínculo, após
confirmação. DRIVER sem vínculo é permitido conforme API, com limite operacional
visível. Não há exclusão física; perfis personalizados seguem o catálogo da OC112.

`CONFIRMADO`: senha inicial/redefinição usam input password, sem armazenamento
local, logs ou echo na resposta. Estados secretos são limpos após resposta e ao
fechar/sair da seção; falha mantém demais dados editáveis. Não envia notificações
ou recuperação por e-mail. Bloqueia submissão duplicada e fechamento enquanto
salva. Último ADMIN, unicidade, auditoria e revogação são regras do servidor.

`CONFIRMADO`: edição de nome/e-mail próprios atualiza AuthProvider; alteração de
segurança própria encerra o contexto e exige novo login. Outros perfis não montam
a funcionalidade e não consultam /users. Temas usam apenas os tokens da #212;
busca global #215 é preservada e continua sem pesquisar usuários administrativos.
Modal reutiliza foco/Escape/retorno do componente existente, com camada acima da
navegação. Nenhuma dependência, migration, MFA/OC98, SSO ou CoreFlow novos.

## Gestão de acessos — UX da OC112

`CONFIRMADO`: Administração → Configurações → Gestão de usuários contém as abas
Usuários e Perfis de acesso. Nome, e-mail, perfil legível, estado, vínculo e ações
mantêm filtros/paginação da OC86. CUSTOM não é rótulo principal da conta; o nome
do perfil associado vem da projeção do servidor.

`CONFIRMADO`: Acesso e permissões permite escolher perfil padrão ou personalizado
ativo. O resumo consulta os quatro perfis fixos pela primeira página de tamanho
4 (contrato ordena esses perfis primeiro); o personalizado usa seu detalhe UUID,
inclusive quando não está na página do seletor. Catálogo traduz módulos/ações;
o resumo informa nome/descrição/estado/quantidades e oferece Ver permissões.
Falha, consulta e ausência de seleção são distintas. Não edita grants no usuário
nem usa um resumo anterior para autorizar ações. UUID continua sendo a atribuição.

`CONFIRMADO`: Gerenciar perfis de acesso abre a outra aba, preservando campos não
secretos do formulário em memória. Senha/confirmar senha são limpas ao alternar;
ao retornar é necessário preenchê-las novamente quando habilitadas. Sair de
Gestão de usuários ou F5 descarta rascunhos e reconsulta a API, sem Web Storage.
Alterar associação/permissões mantém confirmação, revogação e invariantes no
servidor. Perfis fixos, último ADMIN, vínculo DRIVER e escopo CHECKER preservados.

Evidências reais: [OC112 UX](../../../../docs/evidencias/oc112-ux/README.md).
