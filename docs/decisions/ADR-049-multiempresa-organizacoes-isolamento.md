# ADR-049 — Multiempresa SaaS: organizações, vínculos e isolamento

- **Status:** APROVADA para implementação incremental em 14/11/2026; a ativação multi-tenant permanece bloqueada até concluir scoping e testes.
- **Escopo:** LoadX Smart Logistics.
- **Planejamento atual:** [Épico #439](https://github.com/RennaN-C/loadx-smart-logistics/issues/439). Issue #416 preservada como referência histórica.
- **Não altera:** permissões atuais, login, dados, migrações ou deploy do ambiente corrente.

## 1. Contexto verificado

O banco do LoadX atende hoje a um contexto de empresa por instalação:
- `company_profiles` usa um `PROFILE_ID` fixo e constraint singleton. O nome, CNPJ, telefone, email e referência de logo identificam **somente a instalação**, não segregam dados.
- `users.email` é único no conjunto; `users.role` e `custom_profile_id` são globais, sem vínculo de organização.
- `auth_sessions` vincula usuário e token, sem `active_organization_id`.
- Pedidos, frota, produtos, motoristas, clientes, planejamentos, viagens, carregamentos, entregas, anexos, auditoria e Loxi pressupõem esse contexto de dados único.

**Conclusão:** não adicionar apenas `empresa_id` ao login nem aceitar `X-Company-ID` do cliente como autorização. Isso deixaria acesso cruzado possível. O cadastro da empresa atual deve ser preservado até migração completa.

## 2. Fluxo escolhido para o produto

1. Uma empresa solicita acesso publicamente, verifica o contato e aguarda análise pelo proprietário do LoadX. A aprovação cria organização pendente de contratação e convite ao primeiro administrador, sem acesso operacional até pagamento confirmado.
2. Um administrador da organização convida usuários pelo email (convite expirável, token hash, uso único, revogável, auditado); escolhe papel/perfil **naquela organização**.
3. Quem recebe o convite pode já ter conta global. Aceitar convite acrescenta membership, não cria identidade duplicada.
4. Login é por email e senha globais, com MFA como exigido. Após autenticar, se houver uma membership ativa, a organização é selecionada automaticamente; com mais de uma, aparecerá o seletor **antes de entrar na operação**.
5. A API emite sessão associada à organização ativa, validando `membership(user, organization)` e status da organização. Cabeçalho da aplicação exibe organização ativa.
6. Troca de empresa valida novamente membership e gera novo contexto de sessão; evita reutilizar dados/cache do contexto anterior.
7. Revogação do vínculo, suspensão da empresa ou alteração de permissão invalida sessões/concessões relevantes. Nunca permitir a remoção do último administrador ativo.

Exemplo: Empresa Aurora tem 3 usuários com perfis diferentes. O operador B também trabalha na Empresa Norte; ele vê um seletor de empresa após MFA e, em cada contexto, vê só os pedidos/frota/auditoria correspondentes.

## 3. Modelo de dados alvo

`organizations`:
- `id UUID PK`, `legal_name`, `display_name`, `cnpj` (conforme validação de negócio), `status`, `created_at`, `updated_at`.
- A identidade de organização difere do cadastro de dados institucionais atual; migrá-lo sem perder histórico.

`organization_memberships`:
- `id UUID PK`, `organization_id`, `user_id`, `role`, `custom_profile_id` quando aplicável, `status`, `invited_by`, datas.
- `UNIQUE(organization_id, user_id)`. Papéis e perfis customizados pertencem a uma organização, e seus vínculos não atravessam empresas.
- `driver_id` deve ser membership/específico da organização, não único global se um usuário dirigir em mais de uma empresa.

`organization_invitations`:
- `organization_id`, `email_normalized`, `role`, `token_hash`, validade, autor, aceitação, revogação e controle contra repetição.

`auth_sessions`:
- Incluir `active_organization_id` após concluir a migração de segurança e sessão; em estados intermediários, sempre preservar compatibilidade e não habilitar multiempresa.
- A empresa selecionada deve ser validada no servidor em **cada contexto autenticado**, não inferida de ID fornecido pelo frontend.

`organization_id` obrigatório em recursos operacionais:
- Fleet/trucks, products, customers, drivers, order/order items, loads/planos/distribuições, loading sessions, trips/deliveries/ocorrências, uploads/anexos, notificações, agendamento, outbox, auditoria, relatórios e acesso ao Loxi.
- Criar índices e FKs compostas que impeçam vínculo de dados entre organizações; chaves de negócio como código de produto e placa devem avaliar unicidade por organização, não globalmente.
- Preferências de aparência podem continuar por usuário/dispositivo; notificações operacionais devem respeitar organização.

## 4. Regra de isolamento de segurança

- Identidade global é separada de permissão contextual `membership`.
- Todas as consultas, mutações, jobs, fila de eventos, webhooks, exportações, anexos, relatório PDF, busca e ferramentas do assistente recebem contexto de organização **já autenticado**.
- Validar dono/organization de objetos antes de retornar detalhes ou dados; não revelar registros de outra empresa, inclusive via IDs conhecidos.
- PostgreSQL RLS pode ser usado como defesa em profundidade, com contexto por transação; requer configuração cuidadosamente testada de `search_path`, pool de conexões e bypass de serviço.
- Links de arquivos temporários exigem escopo da empresa e autorização de download. Logs, auditoria, índices/caches e IA precisam do mesmo escopo. Não permitir fallback para a empresa padrão em acessos ambíguos.
- Autorização pela API obrigatória, não apenas ocultação de botões no frontend.

## 5. Migração segura do sistema atual

**Fase 0 — contrato e testes:** definir papéis por empresa, entidades, rotas/DTOs e cenários negativos cross-tenant; preparar backup, rollback e feature flag off.

**Fase 1 — estrutura:** criar organizações, membership, convites e campos de sessão, todos inativos para público. Criar organização de legado e vincular usuários existentes, sem alterar o comportamento atual.

**Fase 2 — backfill:** migrar `company_profiles` singleton e marcar TODOS os registros existentes com a organização legado. Migrar permissões/perfis e vínculo de motorista de maneira transacional. Reconciliar contagens, arquivos, outbox e auditoria.

**Fase 3 — isolamento:** aplicar escopo em repositórios SQLAlchemy e endpoints, FK/índices compostos e RLS (se escolhido), depois constraints `NOT NULL`. Cobrir comandos assíncronos e integrações. Revalidar todos os testes e a política de permissões.

**Fase 4 — experiência:** solicitação e aprovação administrativa, convite e aceite, pagamento como gate de liberação, seletor após login/MFA, topo com empresa atual, gestão de membros, remoção de memberships, bloqueio de empresa suspensa, limpeza de cache/estado na troca.

**Fase 5 — pilotagem:** ativar sob feature flag em ambiente isolado com 2 empresas e dados sintéticos; revisar permissões, segurança, desempenho e migração/rollback. Não recriar a antiga branch pentest-lab; o isolamento deve ser de ambiente, banco e dados. Somente depois considerar habilitação comercial.

## 6. Critérios de aceite

- A, B com dados similares: A nunca acessa IDs, listas, resultados de busca, documentos, PDFs, alertas, Loxi ou auditoria de B, mesmo com URL/ID conhecido.
- Trocar empresa altera RBAC, visibilidade e cache, sem confundir perfis/sessões/MFA.
- Convite expirado, repetido, cancelado, para usuário suspenso ou último admin removido são recusados.
- Jobs e outbox carregam `organization_id`; notificação nunca aparece na caixa da outra empresa.
- Aprovação cadastral não libera operações: assinatura e pagamento confirmado são requisitos independentes.
- O núcleo de identidade, organizações e licenças pertence ao LoadX, com futuros módulos de negócio reutilizando esses serviços.
- Testes de migração e backup/rollback aprovados com legado realista antes de qualquer alteração de banco remoto.

## 7. Decisão sobre “Dados da empresa” e outras configurações

**Manter Dados da empresa**: fornece identidade institucional, contatos, eventual exibição em relatórios e futura configuração por organização. **Não confundir** com o futuro seletor de empresa.

**Evitar “Configurações do LoadX” vazias**: preferências de aparência e notificações existentes são controles reais por conta; parâmetros operacionais continuam nos módulos. Não criar toggles que o backend não suporta.

## 8. Limites e pendências

Este ADR aprova a direção e o contrato de segurança, mas **não habilita segunda organização**. A migration 20261114_0036 cria apenas o registro organizacional, memberships, convites, grant singleton vazio e contexto de sessão; não adiciona ainda organization_id aos recursos logísticos nem aplica filtros de tenant. A implementação deve continuar por fases, com migrations auditáveis, scoping de todos os repositórios e relações, testes PostgreSQL de acesso cruzado e revisão de RLS antes de liberar onboarding ou publicar.
