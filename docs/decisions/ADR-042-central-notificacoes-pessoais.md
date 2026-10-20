# ADR-042 — Central pessoal de notificações e autorização da origem

Status: decisão técnica implementada para revisão na OC103 (#150).

## Decisão

`CONFIRMADO`: operational_notifications da OC84 é a única fonte de fatos. A
central não cria eventos administrativos, de documentos/manutenção ou segurança
sem contrato do módulo dono e não altera o mock, claim ou estados da OC84.

notification_recipients associa o fato ao UUID da conta no momento do registro,
com PK (notification_id, user_id), created_at UTC e read_at UTC opcional. O vínculo
é imutável e a primeira leitura é monotônica/idempotente. Uma cópia de leitura por
conta não duplica o evento de domínio. ADMIN recebe sua própria cópia operacional,
sem consulta/alteração de caixas de terceiros. CHECKER sem leitura de viagens
mantém central vazia; perfis personalizados usam grants efetivos da OC112.

Recebem início de viagem: contas ativas com trips.read e a conta DRIVER ativa
vinculada ao motorista da viagem. Ocorrências exigem trips.read + occurrences.read,
ou a identidade DRIVER vinculada. Preferência desabilitada suprime somente novas
associações daquela categoria; nunca apaga fato ou destinatários anteriores.
Associação, fato e histórico usam a mesma transação externa da OC84/OC79. Replay
não recalcula destinatários. Nenhum GET cria associações ou dispara canal.

`CONFIRMADO`: cada consulta/leitura/contador limita user_id à sessão e revalida
permissões atuais. DRIVER exige vínculo ativo e viagem ainda pertencente ao
motorista original. Reatribuição não transfere caixa histórica a outra conta.
Perda de permissão oculta a associação sem excluí-la. O endpoint de origem
revalida também o service do recurso; lista não é autorização para navegar.

Listagem, total filtrado e contador global são calculados em uma única instrução
SQL/snapshot; ordenação por created_at/id, paginação limitada. Marcar todas usa
UPDATE único dos destinatários visíveis e não marca eventos posteriores ao snapshot.
Marcar lida não altera mock_status. Sem endpoints que aceitem user_id destinatário.

notification_preferences tem PK (user_id, category), enabled e updated_at UTC.
TRIPS/OCCURRENCES são configuráveis, SECURITY é obrigatória (CHECK impede false),
sem gerar alertas fictícios. Atualizações por categoria têm last-write-wins; o
INSERT dos destinatários considera preferências confirmadas visíveis à instrução.
Não há retroatividade ao reativar categoria. Alterações efetivas usam USER_UPDATED
na auditoria existente, somente nomes de campos, sem conteúdo de notificação.

## Migração e limites

`CONFIRMADO`: migration 20261020_0026 sobre head real 20261020_0025, aditiva.
Backfill associa fatos OC84 já existentes às contas atualmente elegíveis no corte,
com created_at do recebimento no corte, sem alegar destinatário histórico original.
Não altera, recria ou simula eventos. Novas contas/vínculos posteriores não herdam
esse histórico. Downgrade recusa destinatários/preferências para evitar perda de
leitura ou identidade; nunca apaga operational_notifications.

`CONFIRMADO`: OC109 continua responsável por recuperação de canal/outbox/retries.
A central lê fatos NOT_ATTEMPTED/CLAIMED/FAILED normalmente: são estados do canal,
não da caixa interna. O frontend consulta contratos reais, sem dados ou persistência
fictícios. Categorias futuras entram pelo mesmo serviço após contrato aprovado,
reutilizando regras de documento/manutenção dos módulos donos, sem reimplementá-las.
