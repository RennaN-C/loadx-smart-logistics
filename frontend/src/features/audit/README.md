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
