# Configurações administrativas — estado atual

Página: `/settings`, protegida por ADMIN e pelo backend. Dados pessoais permanecem em `/account` para todos os perfis autenticados.

## Seções administrativas

1. **Dados da empresa** (`#settings-company`): cadastro institucional via `GET/PUT /api/v1/company-profile`. Validações, confirmação explícita, histórico de auditoria e estados de erro permanecem funcionais. Este cadastro é **singleton por instalação**; **não cria nem isola tenants**.
2. **Gestão de usuários** (`#settings-users`): usuários, perfis e permissões, conforme RBAC já implementado.
3. **Integrações e Saúde** (`#settings-integrations`): diagnóstico administrativo somente leitura; estados reais/simulados/limitados separados, atualização manual, filtros por estado e orientações condicionadas ao sinal retornado. Nunca executa teste fictício de envio.
4. **Fila de eventos** (`#settings-outbox`): consulta e reprocessamento autorizado dos eventos existentes, conforme as regras do backend.

Preferências pessoais de tema e notificações foram **concentradas em Meu perfil**, sem duplicação no menu administrativo. Links legados `#settings-preferences`, `#settings-account` e `#settings-logistics` redirecionam para `/account?tab=preferences`. `#settings-profiles` e `#settings-users-profiles` continuam apontando para gestão de usuários.

## Limites reais

- Saúde é uma consulta pontual: API, banco, WhatsApp, IA, webhook e notificações. Não há histórico de uptime, latência p95, logs completos nem inspeção automática do worker nessa tela.
- WhatsApp segue simulado. Disponibilidade de integração interna não prova entrega externa. O painel não expõe segredos ou mensagens privadas.
- Configurações de frota/planejamento continuam nos módulos operacionais. **Não criar toggles de parâmetros inexistentes** nem aparentar que um campo modifica regras sem contrato persistido e testes de efeito.
- O multiempresa foi especificado na [ADR-049](../../../../docs/decisions/ADR-049-multiempresa-organizacoes-isolamento.md) e [issue #416](https://github.com/RennaN-C/loadx-smart-logistics/issues/416). **Não está ativo.** Exige autenticação contextual, memberships, migração controlada e isolamento transversal antes de exibir empresas no login.

## Validação

- Testes: `frontend/src/app/SettingsNavigation.test.tsx`, `frontend/src/features/settings/components/IntegrationHealthPanel.test.tsx`, `frontend/src/features/auth/pages/AccountPage.test.tsx` e os testes específicos de dados institucionais, usuários e outbox.
- Rodar lint, testes, TypeScript/build e verificações E2E de navegação (desktop e celular). Confirmar MFA, autorização 401/403, histórico institucional, links antigos e o funcionamento da fila.
- Não alterar `main`, banco compartilhado, deploy ou release sem aprovação independente.

## Referências

- [ADR-035 — Cadastro institucional](../../../../docs/decisions/ADR-035-configuracoes-institucionais-standalone.md)
- [ADR-049 — Multiempresa e isolamento](../../../../docs/decisions/ADR-049-multiempresa-organizacoes-isolamento.md)
- Histórico de decisões de interface permanece no Git e nas evidências de QA em `docs/evidencias/`.
