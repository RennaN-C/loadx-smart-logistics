# Central de notificações — OC103

`CONFIRMADO`: dados exclusivamente da API /api/v1/notifications. Sem eventos
fictícios, localStorage de notificações, credenciais, dependências novas ou canal
externo. A identidade/vínculo e autorização são decididos no servidor (ADR-042).

- api/notificationsApi: contratos de caixa, leitura, contador, origem e preferências;
- NotificationProvider/Context: contador por sessão, proteção contra respostas
  atrasadas, atualização por navegação/foco e a cada 60 s quando visível;
- NotificationBell/NotificationList: sino, recentes reais, feedback, Escape/foco,
  rolagem interna e link da central sempre visível;
- NotificationsPage: rota autenticada /notifications para todos os perfis,
  filtros/página/ordem na URL, leitura própria individual/em lote e retry;
- NotificationPreferences: Meu perfil (#notification-preferences), consulta,
  edição/salvar/cancelar e segurança obrigatória; rascunho preservado em falha.

`CONFIRMADO`: conta/perfil/grants novos remontam o contexto e eliminam snapshot da
conta anterior. O contador é atualizado pelo envelope real da listagem após mutações;
a central reconsulta ao detectar contagem nova. UI não concede acesso a outra conta.
Origem é obtida por GET autenticado antes da navegação; falha impede navegação e
não anuncia leitura bem-sucedida. Nenhuma viagem ou ocorrência é criada pela central.

Checkboxes/selects/botões nativos, labels, output/alert, foco pós-leitura e Escape
preservam teclado/leitores. Tokens existentes resolvem claro/escuro/automático.
Os testes Vitest simulam somente o transporte; a validação Chromium usa API e
PostgreSQL reais com dados fictícios. Evidências: docs/evidencias/oc103.

`CONFIRMADO`: categorias atuais TRIPS/OCCURRENCES e política obrigatória SECURITY;
nenhum evento de segurança/documento/manutenção é inventado. OC109 não é antecipada.

## UI03 — auditoria #256

`CONFIRMADO`: filtros reutilizam FormField, oferecem limpeza e reiniciam a página.
Sino/central invalidam ações após fechar/navegar; respostas tardias não reabrem a
operação. Uma leitura já enviada pode concluir no servidor, sem navegação posterior.
Trava imediata evita acionamento repetido. Evidências em
[UI03](../../../../docs/evidencias/qa-v12-pentest/ui-lote3.md).
