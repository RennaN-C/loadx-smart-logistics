# Catálogo auditável do Loxi — Issue #371

Base: `73fd043`. Registro executável: `backend/app/modules/assistant/capabilities.py`.
Todos os GET abaixo são verificados contra o OpenAPI em teste. Escopo monoempresa atual; sem ações de escrita.

| Módulo | GET existente | Permissão da orientação | Acesso pelo chat |
|---|---|---|---|
| Conta e segurança | `/api/v1/auth/me` | `usuário autenticado, próprio contexto` | Somente orientação, nenhum segredo/sessão exposto |
| Configurações | `/api/v1/company-profile` | ADMIN + `loadx.settings.manage` | Nome institucional ADMIN; orientação |
| Perfis e permissões | `/api/v1/access-profiles` | ADMIN + `loadx.profiles.manage` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Usuários | `/api/v1/users` | ADMIN + `loadx.users.manage` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Produtos | `/api/v1/products` | `loadx.products.read` | Cadastro paginado (10), orientação |
| Clientes e endereços | `/api/v1/customers` | `loadx.customers.read` | Ativos paginados (10), pedidos/entregas por cliente, orientação |
| Motoristas | `/api/v1/drivers` | `loadx.drivers.read` | Ativos paginados (10), orientação |
| Frota | `/api/v1/trucks` | `loadx.trucks.read` | Cadastro, disponibilidade, utilização, orientação |
| Pedidos | `/api/v1/orders` | `loadx.orders.read` | Lista/status paginados (10), indicadores, orientação |
| Planejamento | `/api/v1/load-plans` | `loadx.planning.read` | Último/específico, histórico (8/página), comparação (2), distribuição (10 partes), sequência (10), orientação |
| Conferência e carregamento | `/api/v1/loading-sessions` | `loadx.loading.read` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Viagens | `/api/v1/trips` | `loadx.trips.read` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Entregas | `/api/v1/deliveries` | `loadx.deliveries.read` | Indicadores por expedição e conclusão, orientação |
| Agenda operacional | `/api/v1/operations/agenda` | `loadx.trips.read` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Relatórios e indicadores | `/api/v1/reports/management-summary` | `loadx.reports.read` | Indicadores com critérios/UTC, orientação |
| Notificações pessoais | `/api/v1/notifications` | `usuário autenticado, próprio contexto` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Auditoria | `/api/v1/audit` | `loadx.audit.read` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Integrações e saúde | `/api/v1/integration-health` | ADMIN + `loadx.integrations.read` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |
| Fila de eventos | `/api/v1/outbox-events` | ADMIN + `loadx.settings.manage` | Orientação documentada e link autorizado; sem consulta de registros desta entidade pelo chat |

As consultas de clientes/motoristas não enviam nomes ao provider; listagens são renderizadas pelo backend e não incluem contatos, documentos ou endereços. Produtos/frota mantêm a semântica de arquivamento anterior. Página explícita é respeitada.

Ferramentas: `get_usage_guidance` seleciona um módulo de enum fechado e revalida sua permissão; `get_registered_customers`, `get_registered_drivers`, `get_registered_orders` reutilizam Services públicos, até dez linhas. Demais ferramentas anteriores permanecem.

Exemplos: “Fale sobre as configurações” (ADMIN, documentação); “Fale sobre os produtos” (documentação); “Liste clientes, página 2” (cadastros ativos, permissão customers.read); “Explique esse planejamento” (snapshot autorizado); “Compare os dois últimos planejamentos” (até dois snapshots); “E o caminhão anterior?” (esclarecimento, sem escolher plano).

Limites: a conversa social gerada é identificada como GENERAL, não consulta registros nem pode publicar indicadores operacionais. Como usar o LoadX usa documentação autorizada. Indicadores e nomes cadastrados continuam vindos do backend; não há SQL livre. Integrações, auditoria, usuários, perfis, eventos, agenda e notificações não ganharam uma API genérica de leitura por IA. Suas consultas diretas pelo chat ficam registradas como lacunas, em vez de simular dados.

Conversa é restrita aos perfis ADMIN/LOGISTICS_MANAGER/CHECKER existentes. DRIVER/CUSTOM continuam sem acesso ao endpoint/painel; não houve mudança de RBAC. Consultas de planos mantêm a restrição CHECKER a aprovados, vigentes e não cancelados.

Navegação documental usa os hashes reais de Configurações e as abas `customers`/`drivers` de Contatos; o frontend mantém allowlist fechada desses destinos.
