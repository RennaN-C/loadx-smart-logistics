# Auditoria

Feature da OC97 para consulta somente leitura do histórico operacional e dos
eventos administrativos selecionados.

- `api/auditApi.ts`: consulta paginada e filtros server-side.
- `pages/AuditPage.tsx`: visão geral para ADMIN e LOGISTICS_MANAGER.
- `components/AuditTrail.tsx`: histórico contextual reutilizável em detalhes.
- nenhum componente desta feature altera ou exclui eventos de auditoria.

`CONFIRMADO`: o catálogo também identifica LOAD_DISTRIBUTION e
LOAD_DISTRIBUTION_PART da OC87, preservando a consulta existente.

`CONFIRMADO` (OC105): catálogo inclui CUSTOMER/PRODUCT/TRUCK/DRIVER e
RECORD_ARCHIVED/RECORD_REACTIVATED, com rótulos em português nos filtros/histórico.

`CONFIRMADO` (OC109): OUTBOX_EVENT/OUTBOX_REPROCESSED identificam intervenções
na fila. Consulta e filtros desses registros são exclusivos do ADMIN; demais
perfis não recebem esses eventos na consulta agregada.

`CONFIRMADO` (UI06): a API resolve em lote o nome atual das entidades existentes
depois da paginação autorizada. A interface mantém o identificador curto na
listagem e revela UUIDs completos somente nos detalhes, traduz estados conhecidos
e converte a tabela em cartões responsivos sem alterar filtros server-side.
Evidências em `docs/evidencias/qa-v12-pentest/ui-lote6.md`.
