# ADR-050 — Control plane comercial e ownership de licenças SaaS

- **Status:** PROPOSTA — requer aprovação antes da implementação.
- **Escopo:** LoadX Smart Logistics, roadmap v1.4.0.
- **Relacionada:** ADR-049 — Multiempresa SaaS: organizações, vínculos e isolamento.
- **Não altera:** código, banco, autenticação, dados ou deploy atuais.

## Contexto

O LoadX atual é monoempresa e standalone. A ADR-049 define a evolução multiempresa e o roadmap v1.4.0 estabelece o CoreFlow como futuro control plane, responsável por organização, identidade global, acesso, licenciamento, entitlements e administração de plataforma.

A nova direção comercial exige solicitações de cadastro, aprovação, catálogo de planos, módulos híbridos, assinaturas, pagamentos automáticos e bloqueio imediato após o período pago.

Criar permanentemente um segundo control plane no domínio logístico duplicaria ownership, identidade, administração e direitos comerciais.

## Decisão proposta

### 1. Ownership por modo de execução

**Modo integrado com CoreFlow**
- CoreFlow é a fonte de verdade de organização, identidade global, memberships globais, operadores de plataforma, catálogo comercial, assinaturas, billing e entitlements.
- LoadX consome contexto e entitlements por contratos autenticados e versionados.
- LoadX mantém somente permissões e regras do domínio logístico.
- Nenhum acesso direto às tabelas ou ao banco do CoreFlow.
- Não existe dupla escrita de assinatura, pagamento, licença ou membership.

**Modo standalone/transição**
- Um adapter local pode implementar temporariamente os contratos de control plane para permitir comercialização antes da disponibilidade do CoreFlow.
- O adapter fica isolado em bounded context próprio e não é importado pelos módulos logísticos.
- Operadores locais são distintos de ADMIN, LOGISTICS_MANAGER, CHECKER e DRIVER.
- A migração para CoreFlow substitui a autoridade do adapter local; IDs externos e vínculos são mapeados por contrato explícito.
- A operação integrada não pode manter duas fontes de verdade.

A escolha do modo de execução para o primeiro lançamento comercial é gate obrigatório de arquitetura.

### 2. Separação de autorização

A autorização efetiva de uma ação exige:
1. organização ativa e membership validada;
2. organização e licença em estado que permita uso;
3. entitlement do módulo/recurso habilitado;
4. permissão logística correspondente.

Entitlement comercial não concede papel administrativo. RBAC logístico não libera módulo comercial.

### 3. Catálogo e versão contratual

- Planos e módulos usam códigos estáveis.
- Versões publicadas de planos são imutáveis.
- Preço, periodicidade, módulos incluídos e limites ficam em snapshot versionado.
- Adicionais contratados são itens explícitos da assinatura.
- Concessões administrativas são temporárias, justificadas e auditadas.
- Alterar o catálogo não modifica contratos já assinados sem regra de migração/consentimento.

### 4. Licença e vencimento

A assinatura é o contrato comercial; a licença efetiva é a projeção dos direitos contratados e do estado financeiro.

O acesso exige organização ativa, assinatura elegível, período pago vigente e entitlement liberado.

A validade termina em paid_through_at. Não existe carência. Cobrança pendente não prorroga período. Pagamento confirmado após o bloqueio pode reativar a licença se o contrato não estiver cancelado ou suspenso. Suspensão administrativa pode bloquear imediatamente com motivo e auditoria.

O vencimento nunca exclui dados operacionais.

### 5. Onboarding

O fluxo obrigatório é solicitação, verificação do contato, revisão administrativa, aprovação/rejeição auditada, convite do primeiro administrador, contratação, pagamento confirmado e ativação.

A solicitação pública não concede acesso operacional. Aprovação não equivale a ativação. O convite é de uso único, expirável e revogável. Identidades globais existentes são reutilizadas.

### 6. Modelo de dados

O modelo lógico inicial e os campos estão em docs/planejamento/v1.4.0/00-visao-geral.md.

As tabelas de catálogo, assinatura, billing e entitlement só devem ser criadas após:
- confirmar o modo standalone ou integrado;
- mapear entidades existentes e ownership;
- revisar a ADR-049;
- definir contrato de sincronização e idempotência;
- validar o modelo físico com migrations PostgreSQL.

Não criar uma tabela platform_admins permanente no domínio logístico. No modo standalone, uma tabela de concessões de operador local pode existir somente dentro do adapter e com caminho de migração definido.

## Consequências

**Positivas**
- Evita duplicar o CoreFlow.
- Permite operar standalone sem acoplar billing ao domínio logístico.
- Separa direito comercial de permissão operacional.
- Facilita trocar o adapter local pelo CoreFlow.
- Mantém auditoria, expiração e concessões explícitas.

**Custos e riscos**
- Exige contratos e adapters bem definidos.
- Exige migração cuidadosa do legado e de todas as consultas para tenancy.
- O modo inicial de operação precisa ser escolhido antes de implementar administração e billing.
- Sincronização externa exige autenticação serviço-a-serviço, idempotência, reconciliação e tratamento de indisponibilidade.

## Alternativas rejeitadas

- Colocar assinatura, pagamento e plano diretamente em users ou company_profiles.
- Usar ADMIN do LoadX como SUPERADMIN de plataforma.
- Confiar em organization_id/X-Company-ID enviado pelo frontend.
- Duplicar no LoadX e CoreFlow a mesma assinatura ou entitlement.
- Liberar acesso apenas ocultando menus no frontend.

## Critérios de aceite

- Ownership por modo de execução documentado e testado.
- Nenhuma rota logística consulta billing diretamente.
- Nenhum entitlement é aceito sem origem autenticada.
- Operador de plataforma não recebe automaticamente acesso operacional aos dados da empresa.
- Troca de modo/adapter preserva IDs, contratos e histórico.
- Testes demonstram isolamento entre empresas e separação entre entitlement e RBAC.
