# ADR-050 — LoadX como plataforma SaaS autônoma e modular

- **Status:** ACEITA como direção de produto em 14/11/2026; implementação depende de contratos, migrações e testes.
- **Escopo:** evolução multiempresa e comercial do LoadX, com expansão setorial futura.
- **Relacionadas:** ADR-049 (multiempresa e isolamento), ADR-051 (integração de pagamentos).
- **Não altera:** código, dados, autenticação nem deploy.

## Contexto

O LoadX é atualmente uma aplicação de logística monoempresa, com autenticação, permissões, otimização de cargas e visualização 3D. A evolução aprovada cria uma plataforma SaaS que aceita várias organizações, solicitações de cadastro, aprovação pelo proprietário, planos, módulos híbridos, cobrança automática, licenças e controle de acesso.

O **LoadX é proprietário integral e definitivo de seu núcleo de plataforma**. Não depende de outro produto para identidade, organizações, pagamentos, licenciamento, entitlements ou administração.

## 1. Núcleo único: LoadX Platform

O núcleo SaaS mantém uma fonte de verdade para:
- identidade global, autenticação, MFA e sessões;
- organizações, solicitações, convites e memberships;
- administração geral e auditoria da plataforma;
- catálogo de planos e módulos, versões, preços, limites e adicionais;
- assinaturas, faturas, pagamentos, reconciliação, licenças e entitlements.

Os módulos de negócio usam interfaces de identidade, tenant, autorização e entitlement do núcleo, sem duplicar seus bancos de contas ou cobrança.

## 2. Administrador geral exclusivo

O papel `PLATFORM_OWNER` pertence inicialmente a **uma única identidade autorizada**. Não existe cadastro público, interface para promover alguém a esse papel ou autoelevação. Concessão e recuperação excepcional de acesso requerem mecanismo restrito e auditável.

`PLATFORM_OWNER` é diferente de `ADMIN` da organização, `LOGISTICS_MANAGER`, `CHECKER` e `DRIVER`.

Ser proprietário da plataforma não significa receber automaticamente acesso de leitura a informações operacionais confidenciais de uma transportadora. Acesso excepcional de suporte exige justificativa, autorização, duração limitada e auditoria.

## 3. Módulos e fronteiras

**LoadX Logistics** será o primeiro módulo de negócio comercial e contém cadastros logísticos, produtos, pedidos, frota, motoristas, otimização/planejamento de carga, carregamento, viagens, entregas, documentos, relatórios e Loxi com contexto autorizado.

**LoadX 3D** é uma possibilidade futura de módulo/capacidade reutilizável. O visualizador atual continuará integrado e destacado no planejamento, reproduzindo resultados autorizados do algoritmo. Uma futura biblioteca/capacidade de cena não substitui as validações físicas, limites e regras do otimizador. Qualquer comercialização separada de 3D depende de API, autorização, limites, dados e modelo de preço próprios.

**Outros nichos** poderão receber módulos de domínio distintos com suas próprias permissões, dados e fluxos, usando o mesmo núcleo SaaS. Nenhuma dessas expansões integra automaticamente a v1.4.0.

Adotar **monólito modular**, sem microserviços prematuros; separar responsabilidades por contratos internos estáveis. A independência de módulos é lógica/arquitetural, não exige deploy ou banco isolado para cada módulo.

## 4. Autorização efetiva

Toda ação operacional exige simultaneamente:
1. usuário autenticado e organização ativa validada no backend;
2. membership válida e permissão naquela organização;
3. organização ativa e em estado permitido;
4. assinatura elegível, período já pago vigente e entitlement do módulo;
5. limites contratados verificados pelo serviço de domínio.

RBAC operacional não concede um entitlement comercial e um entitlement comercial não concede privilégios operacionais.

Nunca autorizar pelo `organization_id` enviado livremente pelo frontend. A autorização e o isolamento devem abranger banco, API, workers, relatórios, anexos, notificações, auditoria, pesquisa e Loxi, conforme ADR-049.

## 5. Planos, assinatura e vencimento

- Planos publicados usam versões imutáveis, com preço, ciclo, módulos e limites.
- Contratações conservam o snapshot do que foi aceito.
- Módulos adicionais contratados são itens explícitos da assinatura.
- Concessões manuais são temporárias, justificadas e auditadas.
- A assinatura não se confunde com fatura, pagamento nem entitlement.
- A validade da licença é determinada pelo instante UTC `paid_through_at`, a partir do servidor/banco.
- Ao terminar o período pago, o bloqueio é **imediato**, sem tolerância.
- Cobrança pendente não estende licença.
- Pagamento autenticado e confirmado pelo gateway pode renovar/reativar, conforme estado contratual.
- Suspensão administrativa pode bloquear imediatamente, com motivo e auditoria.
- O vencimento não apaga dados; o portal financeiro permanece acessível para regularização.

## 6. Onboarding híbrido

1. Solicitação pública com validação e verificação do contato.
2. Aprovação ou rejeição exclusiva pelo proprietário do LoadX.
3. Organização criada em estado pendente e convite ao primeiro administrador.
4. Primeiro administrador aceita convite e escolhe contratação.
5. Checkout do provedor de pagamento.
6. Webhook autenticado e conferência financeira no provedor.
7. Licença ativada e entitlements calculados; empresa acessa operações.

Aprovação não dá acesso operacional e redirect do checkout não comprova pagamento.

## 7. Dados e migrations

Criar organização legada, executar backfill de cadastros e registros existentes, revisar escopo de índices e FKs, impedir vínculos cross-tenant e validar isolamento em todas as rotas e jobs.

Garantir upgrade e rollback seguros, preservação de histórico, testes PostgreSQL, feature flags e homologação com duas organizações. Avaliar RLS somente com testes reais de papéis de banco, pool, workers e possibilidade de bypass.

O modelo lógico candidato está em `docs/planejamento/v1.4.0/00-visao-geral.md`; nomes e estruturas físicas requerem revisão antes de migrations.

## Consequências

**Benefícios:** plataforma única independente, licença centralizada, faturamento consistente, módulo logístico preservado e base para expansão multissetorial.

**Custos/riscos:** maior responsabilidade por segurança, cobrança, suporte, LGPD e isolamento; migração ampla de monoempresa para multiempresa; necessidade de idempotência e reconciliação financeira.

## Alternativas rejeitadas

- Fazer depender o núcleo do LoadX de outra plataforma administrativa.
- Duplicar identidades, cadastros de empresas, assinaturas ou pagamentos.
- Usar `ADMIN` logístico como proprietário da plataforma.
- Tratar ocultação de menus como controle de segurança.
- Criar automaticamente novos módulos setoriais ou separar 3D do otimizador antes de validar seus contratos.

## Critérios de aceite

- Núcleo SaaS pertence integralmente ao LoadX, sem dependência externa para autoridade de identidade ou licença.
- Somente a identidade proprietária possui autorização de administração central.
- O proprietário não herda acesso irrestrito a dados operacionais.
- Tenancy, entitlement, RBAC e pagamento são verificações distintas e obrigatórias.
- Contratos, faturas e eventos preservam histórico, idempotência e trilhas de auditoria.
- O planejamento logístico e seu 3D continuam funcionando integralmente.
- A inclusão futura de outros módulos não exige reconstruir login, cadastro de empresas ou pagamentos.
