# v1.4.0 — SaaS multiempresa, licenciamento e cobrança

**Status:** planejamento técnico aprovado para detalhamento e abertura de Issues. Implementação, alteração de banco remoto, ativação de cobrança e publicação ainda não autorizadas.

**Escopo:** transformar o LoadX em uma solução SaaS multiempresa, com entrada controlada de clientes, planos comerciais, módulos híbridos, assinaturas, pagamentos automáticos e administração da plataforma.

## 1. Decisões comerciais confirmadas

| Tema | Decisão |
|---|---|
| Cobrança | Automática, por provedor integrado e eventos validados |
| Licenciamento | Híbrido: módulos do plano, adicionais e concessões administrativas controladas |
| Vencimento | Bloqueio imediato ao fim do período efetivamente pago, sem carência |
| Onboarding | Solicitação → aprovação administrativa → contratação/pagamento → liberação |
| Provedores em avaliação | Asaas e Mercado Pago |
| Primeiro provedor | Pendente de avaliação comercial, elegibilidade e homologação |

O pagamento automático descreve a geração e conciliação automatizada das cobranças. O débito também será automático somente quando o meio de pagamento oferecer essa capacidade e o pagador tiver autorizado: cartão recorrente ou Pix Automático elegível. Pix comum e boleto podem gerar cobranças recorrentes sem débito automático; nesses casos, o cliente precisa efetuar o pagamento de cada cobrança.

## 2. LoadX como plataforma SaaS autônoma e modular

**DECISÃO DE PRODUTO (14/11/2026):** o LoadX será o responsável permanente pelo seu próprio núcleo SaaS, sem depender de outra plataforma para identidade, organizações, administração, planos, licenças, pagamentos ou módulos.

### Núcleo LoadX Platform
- Login, MFA, sessões, usuários e identidades globais.
- Empresas, solicitações, aprovações e memberships por organização.
- Administração geral exclusiva do proprietário do LoadX, separada dos administradores das empresas.
- Planos, módulos, limites, adicionais, assinaturas, cobrança e entitlements.
- Auditoria administrativa e integração com gateways.

O papel `PLATFORM_OWNER` será inicialmente concedido apenas a uma identidade autorizada, sem cadastro público nem autoelevação. Um procedimento excepcional de recuperação precisa ser seguro e auditado. O proprietário da plataforma não ganha acesso automático a informações operacionais privadas dos clientes.

### Primeiro módulo de negócio
**LoadX Logistics** continua sendo o produto comercial inicial: clientes, produtos, pedidos, frota, motoristas, planejamento e otimização de cargas, carregamento, viagens, entregas e relatórios.

### Módulos para outros nichos
No futuro, o mesmo núcleo poderá atender novas atividades e setores por módulos de negócio próprios, cada um com dados, permissões, limites e entitlements. **Novos nichos não fazem parte da implementação v1.4.0.**

### Papel do 3D
O 3D atual permanece integrado e destacado no planejamento de cargas, exibindo o resultado real do algoritmo, sem decidir ou recalcular validade física no frontend.

No futuro, componentes de visualização 3D poderão ser extraídos para uma capacidade compartilhada, com contratos versionados de cenas, objetos e unidades, reutilizável por outros módulos. Um produto comercial autônomo "LoadX 3D" é hipótese futura e não dá acesso às regras de negócio/otimizador logístico sem o entitlement correspondente.

### Direção técnica
Preservar monólito modular com FastAPI, SQLAlchemy, PostgreSQL e React; separar núcleo SaaS, módulos de negócio e capacidade visual com fronteiras explícitas. Não antecipar microserviços ou novos bancos sem necessidade comprovada.

## 3. Domínios e ownership

| Domínio | Responsabilidade |
|---|---|
| Organizations | Identidade e estado da organização |
| Identity | Conta global do usuário |
| Memberships | Vínculo e papel do usuário em cada organização |
| Platform Operations | Solicitações, aprovação e administração central da plataforma |
| Catalog | Planos, versões, módulos, adicionais e limites |
| Subscriptions | Contratos e períodos de assinatura |
| Billing | Clientes do provedor, faturas, pagamentos e conciliação |
| Licensing | Ciclo de vida comercial e eventos da licença |
| Entitlements | Direitos efetivos de módulos e limites |
| LoadX Logistics | Regras, dados e permissões operacionais |
| Shared 3D (futuro) | Componentes reutilizáveis de visualização, sem substituir a lógica física logística |

Permissão logística e entitlement comercial são verificações independentes. Um usuário precisa ter ambas para executar uma funcionalidade: o plano precisa liberar o módulo e o membership precisa autorizar a ação.

## 4. Onboarding de empresas

Fluxo proposto:

1. O interessado envia uma solicitação pública com dados mínimos da empresa e do contato responsável.
2. O sistema valida formato, normaliza e-mail/CNPJ, limita tentativas e verifica o e-mail do contato antes de concluir a análise.
3. A solicitação fica em análise; ainda não existe acesso operacional nem licença.
4. Um operador autorizado aprova ou rejeita a solicitação, registrando ator, horário e motivo.
5. Na aprovação, o sistema cria a organização em estado pendente de contratação e envia um convite seguro ao primeiro administrador da empresa.
6. O convidado aceita o convite. Se já possuir conta global, recebe apenas um novo membership; não é criada identidade duplicada.
7. O administrador escolhe o plano e os adicionais permitidos e conclui o checkout hospedado pelo provedor.
8. O backend recebe e valida o evento do pagamento, consulta o recurso financeiro no provedor e confirma a cobrança.
9. A assinatura passa a ativa, os entitlements são materializados e a organização pode entrar no ambiente operacional.
10. O usuário autentica, seleciona a organização quando possuir mais de uma e entra no LoadX somente após as verificações de membership, estado da organização, licença e permissões.

Estados mínimos da solicitação: SUBMITTED, EMAIL_VERIFICATION_PENDING, IN_REVIEW, APPROVED, REJECTED, CANCELED e EXPIRED. Transições administrativas devem ser auditadas e não podem ser executadas pelo próprio solicitante.

A solicitação pública não cria uma conta privilegiada nem permite escolher o próprio status. A aprovação não libera o sistema; o pagamento confirmado é que ativa a licença.

## 5. Identidade, membership e isolamento

Seguir a ADR-049:
- manter a identidade global separada dos vínculos organizacionais;
- usar membership para armazenar papel e perfil dentro de cada organização;
- permitir que uma identidade participe de várias organizações;
- associar a sessão autenticada à organização ativa, validada no servidor;
- não confiar em X-Company-ID, organization_id de body ou query como autorização;
- trocar de organização revogando ou substituindo o contexto anterior e limpando caches/estado sensível;
- impedir remoção ou rebaixamento do último administrador ativo de uma organização.

O domínio logístico deverá receber organization_id obrigatório em todos os agregados e recursos identificados na ADR-049: clientes, motoristas, caminhões, produtos, pedidos, itens, planejamentos, distribuições, carregamentos, viagens, entregas, ocorrências, anexos, notificações, auditoria, relatórios, agenda, busca, integrações e contexto do Loxi.

As migrations devem:
- criar primeiro a organização legada;
- vincular todos os registros existentes a ela em backfill transacional;
- preservar UUIDs, histórico, auditoria, anexos, notificações e outbox;
- revisar unicidades para escopo organizacional;
- criar FKs compostas que impeçam relacionamentos entre organizações;
- validar contagens antes e depois do backfill;
- manter feature flag desativada até os testes negativos de isolamento passarem.

O escopo por organização na aplicação é obrigatório. PostgreSQL RLS pode ser adotado como defesa em profundidade após prova específica com o pool de conexões, SET LOCAL, papéis de runtime/migration, workers e testes de bypass. Não declarar RLS como proteção efetiva sem comprovar que a role de runtime não pode ignorá-lo.

Jobs, outbox, webhooks, relatórios PDF, anexos, URLs temporárias, busca, cache e Loxi precisam transportar e validar o mesmo contexto organizacional. Nenhum fallback pode selecionar silenciosamente a organização legada.

## 6. Catálogo comercial e licenciamento híbrido

### Planos

Os planos são registros configuráveis, não condicionais espalhadas pelo código. Cada plano publicado referencia uma versão imutável.

Estados de versão: DRAFT, PUBLISHED e RETIRED. Alterar preço, módulos ou limites gera uma nova versão; assinaturas existentes preservam o snapshot contratado até uma alteração contratual explícita.

### Módulos

O catálogo de módulos usa códigos estáveis e metadados:
- código e nome;
- descrição comercial;
- dependências de outros módulos;
- disponibilidade para contratação;
- regras de limite;
- versão mínima do produto, quando necessário.

O plano híbrido combina:
1. módulos incluídos na versão do plano;
2. módulos adicionais recorrentes contratados;
3. concessões administrativas temporárias, com motivo, ator, início e expiração.

Concessões manuais não podem ser permanentes por acidente, não substituem pagamento e precisam de trilha de auditoria. Dependências são validadas no servidor; não é possível liberar um módulo dependente sem seus requisitos.

### Limites

Limites configuráveis por plano podem incluir usuários, caminhões, operações, volume de otimizações, consumo de IA e armazenamento. O catálogo define o valor; serviços de domínio aplicam a regra. Não duplicar limites no frontend.

A visualização 3D atual permanece integrada ao planejamento de cargas. Um futuro módulo reutilizável de visualização 3D dependerá de contratos de cena próprios; não concede automaticamente acesso ao algoritmo ou aos dados logísticos.

### Modelo lógico proposto

| Entidade | Responsabilidade |
|---|---|
| organizations | Empresas |
| organization_memberships | Vínculos e papéis |
| organization_invitations | Convites seguros |
| registration_requests | Solicitações públicas |
| platform_operator_grants | Concessões administrativas globais, inicialmente apenas ao proprietário da plataforma |
| plans | Catálogo de planos |
| plan_versions | Snapshot imutável de preço e regras |
| modules | Catálogo de módulos |
| plan_modules | Módulos incluídos por versão |
| plan_limits | Limites por versão |
| subscriptions | Contrato e ciclo de cobrança |
| subscription_items | Adicionais contratados |
| billing_customers | Identificadores de cliente em cada provedor |
| billing_invoices | Faturas e vencimentos |
| billing_invoice_items | Snapshot de itens e valores |
| payments | Tentativas e recebimentos |
| payment_webhook_events | Inbox idempotente de eventos externos |
| organization_entitlements | Direitos efetivos calculados |
| license_events | Histórico de ativação, suspensão, expiração e concessões |

O nome e o desenho físico definitivos serão revisados com os models existentes antes de criar migrations. Não criar tabela redundante para algo já coberto por uma entidade atual sem justificar a separação.

## 7. Assinatura, fatura e ciclo da licença

A assinatura representa o contrato comercial; faturas representam cobranças de um ciclo; pagamentos representam tentativas/recebimentos; entitlements representam os direitos efetivos.

Estados propostos para assinatura:
- PENDING_PAYMENT: contratação aprovada, aguardando primeiro pagamento;
- ACTIVE: período contratado e pago vigente;
- PAST_DUE: tentativa de renovação falhou, mas o período já pago ainda não terminou;
- CANCELED: renovação encerrada; acesso permanece somente até o fim do período já pago, salvo suspensão administrativa;
- EXPIRED: período pago terminou sem renovação confirmada;
- SUSPENDED: suspensão administrativa explícita.

Estados financeiros devem distinguir PENDING, AUTHORIZED, PAID/CONFIRMED, FAILED, CANCELED, REFUNDED e CHARGEBACK, respeitando o vocabulário e o mapeamento de cada gateway.

Campos temporais devem usar UTC e distinguir:
- period_start;
- period_end / paid_through_at;
- invoice_due_at;
- paid_at;
- canceled_at;
- suspended_at.

### Regra de vencimento imediato

Acesso comercial válido exige que o instante atual do banco seja anterior a paid_through_at, além de organização ativa, assinatura elegível e entitlement do módulo habilitado.

- Não existe período de carência após paid_through_at.
- Cobrança pendente não prorroga a licença.
- Pagamento confirmado antes do limite renova o período conforme o contrato.
- Pagamento confirmado depois do bloqueio pode reativar o acesso após reconciliação e validação do estado da assinatura.
- Cancelamento de renovação não apaga o período já pago.
- Suspensão administrativa pode bloquear imediatamente, mesmo com período pago, desde que motivo e ator sejam auditados.
- Vencimento nunca apaga dados operacionais.

A data de vencimento comercial e o período pago precisam ser apresentados claramente ao cliente. Não usar o horário local do navegador para decidir bloqueio.

## 8. Provedores de pagamento

### Comparativo preliminar

| Critério | Asaas | Mercado Pago |
|---|---|---|
| Assinaturas por API | Sim | Sim |
| Cartão recorrente | Sim | Sim |
| Pix e boleto | Sim | Sim |
| Pix Automático | Documentado, sujeito a elegibilidade da conta | Não confirmado no produto de assinaturas avaliado |
| Webhook autenticado | Token de acesso do webhook | Assinatura HMAC |
| Retentativas | Conforme produto/configuração | Retentativas automáticas documentadas |
| Sandbox | Sim | Sim |
| Condições comerciais | Dependem da conta/contrato | Dependem da conta/contrato e produto |

### Asaas

A documentação oficial descreve API REST, clientes, cobranças, assinaturas recorrentes, Checkout hospedado e webhooks. As assinaturas podem gerar cobranças periódicas por boleto, Pix ou cartão. A criação da assinatura não confirma recebimento; cada cobrança precisa ser conciliada.

O Pix Automático permite débito recorrente após autorização do pagador. A documentação consultada informa requisitos para a conta recebedora, incluindo PJ, CNPJ ativo há pelo menos seis meses, cadastro aprovado, CNAE compatível e chave Pix ativa. A disponibilidade deve ser confirmada na conta comercial real.

Fontes:
- https://docs.asaas.com/docs/visao-geral
- https://docs.asaas.com/docs/assinaturas
- https://docs.asaas.com/docs/checkout-asaas
- https://docs.asaas.com/docs/pix-automatico
- https://docs.asaas.com/docs/webhooks-2
- https://www.asaas.com/precos-e-taxas

### Mercado Pago

A documentação oficial descreve API de assinaturas com ou sem plano associado, frequência recorrente, faturas, pagamentos e tentativas automáticas. A documentação de assinaturas lista meios online e offline, incluindo Pix e boleto.

O produto avançado de pagamentos automáticos sem CVV, baseado em cartão armazenado e transações iniciadas pelo comerciante, requer habilitação comercial e possui requisitos próprios. Não confundir esse produto com a geração de faturas recorrentes via assinatura.

Webhooks usam assinatura secreta HMAC no header x-signature e precisam de validação antes de processar eventos.

Fontes:
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/additional-content/your-integrations/notifications/webhooks
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/overview
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/prerequisites

### Recomendação

Asaas é o candidato preliminar para a primeira integração por combinar API de cobrança/assinatura, Checkout e possibilidade de Pix Automático. Mercado Pago permanece alternativa válida, especialmente para assinaturas e cartão recorrente.

A decisão final exige:
- proposta comercial/tarifário aplicado à conta do LoadX;
- confirmação de elegibilidade para Pix Automático ou produto equivalente;
- custos por Pix, boleto, cartão, estorno e antecipação;
- prazos de liquidação e disponibilidade de saldo;
- retentativas e regras de inadimplência;
- limites de API, suporte, Sandbox e processo de homologação;
- teste ponta a ponta dos meios que serão realmente oferecidos.

Tarifas públicas não são diretamente comparáveis entre produtos e prazos diferentes. Não fixar preço do LoadX usando taxas promocionais ou sem confirmar a condição comercial efetiva.

## 9. Arquitetura de integração de pagamento

Criar uma porta de domínio BillingGateway e adapters independentes por provedor. O domínio não importa SDK nem conhece payload específico do Asaas/Mercado Pago.

Operações mínimas da porta:
- criar ou localizar cliente no provedor;
- criar checkout de primeira contratação;
- criar/gerenciar recorrência quando suportada;
- consultar pagamento, fatura e assinatura;
- cancelar renovação ou assinatura;
- validar autenticidade de webhook;
- normalizar evento externo para evento interno.

O primeiro release integra somente um provedor. O segundo adapter poderá ser implementado sem alterar regras de assinatura ou licença. Não migrar tokens/cartões entre provedores automaticamente; mudança de provedor exige novo consentimento/checkout quando aplicável.

### Segurança e consistência

- Preferir Checkout hospedado/tokenização do provedor. O LoadX não armazena PAN ou CVV.
- Segredos de API ficam somente no backend/secret manager, nunca no frontend, logs ou repositório.
- Cada criação de checkout/cobrança usa chave de idempotência e referência interna estável.
- O retorno do navegador não confirma pagamento.
- Webhook é público apenas no sentido de não usar sessão do usuário; exige autenticação criptográfica/token específica do provedor.
- Persistir o recebimento do evento antes de trabalho demorado e responder rapidamente.
- Deduplicar por provedor + identificador externo do evento; quando não existir ID estável, usar chave de deduplicação definida pelo adapter.
- Consultar o recurso financeiro no provedor antes de marcar pagamento como confirmado.
- Processar mudanças de pagamento, fatura, assinatura e entitlement em transação consistente.
- Reprocessamento é seguro e idempotente; eventos fora de ordem não podem reativar assinatura cancelada/suspensa indevidamente.
- Manter reconciliação periódica para detectar eventos perdidos e divergências.
- Não armazenar payload bruto com dados sensíveis sem necessidade; preferir metadados mínimos, hash, IDs externos e resultado de validação.

Endpoint proposto: POST /api/v1/billing/webhooks/{provider}. Endpoints administrativos e do cliente ficam autenticados e respeitam RBAC, membership e entitlement.

## 10. Contratos de API candidatos

Os caminhos finais serão versionados em docs/05 antes da implementação.

| Área | Operação candidata |
|---|---|
| Cadastro público | POST /public/registration-requests |
| Administração | GET /platform/registration-requests |
| Aprovação | POST /platform/registration-requests/{id}/approve |
| Rejeição | POST /platform/registration-requests/{id}/reject |
| Empresas | GET /platform/organizations |
| Suspensão | POST /platform/organizations/{id}/suspend |
| Catálogo público | GET /catalog/plans |
| Assinatura da empresa | GET /billing/subscription |
| Checkout | POST /billing/checkout |
| Faturas | GET /billing/invoices |
| Entitlements | GET /organizations/current/entitlements |
| Convites | POST /organizations/current/invitations |
| Troca de organização | POST /auth/organization-context |
| Webhook | POST /billing/webhooks/{provider} |

Nenhum endpoint pode confiar em organization_id fornecido livremente pelo cliente para decidir acesso. A organização vem do contexto autenticado e validado.

## 11. Interfaces

### Administração geral da plataforma LoadX

- Dashboard comercial e operacional;
- solicitações de cadastro e análise;
- organizações e estado de cada conta;
- catálogo de planos, versões, módulos e limites;
- assinaturas, licenças e concessões temporárias;
- faturas, pagamentos, falhas e conciliação;
- auditoria da plataforma;
- saúde dos adapters e fila de webhooks.

O proprietário da plataforma é separado dos administradores de cada empresa. Não existe cadastro público de operador, autoelevação ou acesso operacional irrestrito aos dados dos clientes. Acesso excepcional de suporte deve ser temporário, justificado e auditado.

### Portal da empresa

- plano e módulos contratados;
- usuários e convites da organização;
- assinatura e período pago;
- próxima cobrança;
- faturas e pagamentos;
- atualizar meio de pagamento pelo fluxo seguro do provedor;
- contratar adicional permitido;
- cancelar renovação;
- avisos de vencimento e estado da licença.

### Navegação operacional

O frontend pode ocultar módulos sem entitlement para melhorar a experiência, mas isso não é segurança. O backend deve aplicar entitlement e permissão em cada rota, service e ação.

## 12. Plano de entregas e dependências

| Fase | Entrega | Dependência / gate |
|---|---|---|
| 0 | Inventário de tabelas, rotas, jobs e contratos do núcleo SaaS; ADRs revisadas; avaliação comercial dos gateways | Antes de migrations |
| 1 | Organizações, memberships, sessão contextual e backfill do legado | Fase 0; testes cross-tenant |
| 2 | Solicitação pública, verificação de e-mail, análise, aprovação e convite do primeiro administrador | Fase 1 |
| 3 | Catálogo versionado, módulos, adicionais, limites e serviço de entitlements | Fases 1 e 2 |
| 4 | Assinaturas, faturas, pagamentos e máquina de estados da licença | Fase 3 |
| 5 | Adapter do provedor escolhido, checkout, webhooks, idempotência e reconciliação | Fase 0 e 4 |
| 6 | Painel geral do LoadX e portal financeiro do cliente | Contratos de API das fases 2–5 |
| 7 | Homologação, teste de isolamento, segurança, carga, recuperação e piloto com duas organizações | Todas as fases |

A ordem detalhada de execução pode sobrepor trabalho de interface e documentação, mas a liberação comercial depende de todos os gates anteriores.

## 13. Critérios globais de aceite

### Multiempresa e identidade
- Usuário com múltiplas memberships escolhe organização antes de acessar dados.
- A troca de organização invalida o contexto anterior e limpa cache/estado.
- A, B nunca acessa registros, arquivos, relatórios, auditoria, busca ou Loxi de B, mesmo usando UUID conhecido.
- FKs compostas impedem relacionar entidades de organizações diferentes.
- Jobs, workers, outbox, anexos e relatórios preservam o tenant.

### Onboarding e administração
- Solicitação não cria acesso operacional.
- Somente operador autorizado aprova/rejeita.
- Aprovação cria convite seguro e organização pendente de pagamento.
- Convites são expiráveis, revogáveis, de uso único e auditados.
- Membership existente é reutilizada sem duplicar usuário global.

### Catálogo e licença
- Plano publicado é imutável; alteração gera nova versão.
- Módulos adicionais e dependências são validados no backend.
- Limites são aplicados no backend e não apenas na interface.
- Override tem motivo, ator, início e expiração.
- Licença expira no instante definido sem carência; dados não são apagados.

### Pagamento
- Webhook inválido não altera pagamento ou licença.
- Evento repetido não duplica pagamento, fatura ou renovação.
- Redirect de sucesso não ativa licença.
- Pagamento só é confirmado após validação e consulta ao provedor.
- Evento atrasado ou fora de ordem não reativa contrato cancelado/suspenso incorretamente.
- Pagamento confirmado após expiração reativa conforme estado contratual.
- Reconciliação detecta eventos perdidos e divergências.
- Nenhum dado bruto de cartão é armazenado.

### Qualidade e publicação
- Migrations testadas em PostgreSQL 16 com upgrade, backfill, rollback seguro e reconciliação.
- Pytest, Ruff, Vitest, TypeScript, ESLint, E2E e CI aprovados.
- Testes negativos cross-tenant obrigatórios.
- Sandbox do provedor validado para aprovação, recusa, duplicata, atraso, cancelamento, reembolso e chargeback.
- Piloto com duas organizações isoladas e dados não confidenciais.
- Nenhum deploy, release ou ativação de cobrança real sem autorização explícita e checklist de produção aprovado.

## 14. Decisões ainda pendentes

1. Definir contratos entre o núcleo SaaS e módulos setoriais, com caminho para evolução futura do 3D sem comprometer a logística.
2. Escolher o gateway inicial após comparar propostas comerciais e homologar os fluxos reais.
3. Definir preços, ciclos mensais/anuais, descontos e política de reajuste.
4. Definir período de teste gratuito, se haverá.
5. Definir política de cancelamento imediato versus fim do período pago.
6. Definir tratamento comercial de reembolso, chargeback e inadimplência após o bloqueio.
7. Definir pró-rata ao adicionar/remover módulos no meio do ciclo.
8. Definir documentos fiscais e integração de emissão de NFS-e, se necessária.
9. Definir política de retenção e exportação dos dados após encerramento da empresa.

Nenhuma dessas pendências autoriza inventar comportamento no código. Devem virar decisão explícita antes do contrato afetado.

## 15. Limites desta entrega documental

Este planejamento não altera o comportamento do LoadX. Não cria tabelas, não modifica autenticação, não altera os dados existentes, não integra gateway, não habilita multiempresa, não executa migration, não altera secrets e não realiza deploy ou release.

A implementação começa por Issues pequenas, com responsável, contrato, critérios de aceite e testes definidos, respeitando a branch desenvolvimento e os gates de revisão do repositório.


## 16. Rastreamento no GitHub

Epic: [#439 — Plataforma comercial e licenciamento do LoadX](https://github.com/RennaN-C/loadx-smart-logistics/issues/439)

- [#440 — Gate: contratos da plataforma e gateway](https://github.com/RennaN-C/loadx-smart-logistics/issues/440)
- [#441 — Fundação multiempresa e migração legada](https://github.com/RennaN-C/loadx-smart-logistics/issues/441)
- [#442 — Onboarding, aprovação e convites](https://github.com/RennaN-C/loadx-smart-logistics/issues/442)
- [#443 — Catálogo de planos, módulos e limites](https://github.com/RennaN-C/loadx-smart-logistics/issues/443)
- [#444 — Assinaturas, entitlements e vencimento](https://github.com/RennaN-C/loadx-smart-logistics/issues/444)
- [#445 — Gateway, checkout, webhooks e conciliação](https://github.com/RennaN-C/loadx-smart-logistics/issues/445)
- [#446 — Painel de plataforma e portal financeiro](https://github.com/RennaN-C/loadx-smart-logistics/issues/446)
- [#447 — Homologação e piloto](https://github.com/RennaN-C/loadx-smart-logistics/issues/447)

A Issue [#430](https://github.com/RennaN-C/loadx-smart-logistics/issues/430) permanece independente e não faz parte deste épico.
