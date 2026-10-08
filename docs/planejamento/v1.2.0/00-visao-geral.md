# Planejamento da v1.2.0

## Objetivo

`CONFIRMADO`: a v1.2.0 consolida o LoadX como produto operacional monoempresa
e standalone antes da futura camada de multi-tenancy logístico e integração com
CoreFlow planejada para a v1.3.0. A versão fecha lacunas de administração, segurança,
comunicação, frota, operação, cadastros, auditoria, pesquisa e relatórios.

`CONFIRMADO`: a versão usa **OC79–OC112**, formalizadas nas Issues **#122–#133**,
**#136–#141** e **#144–#159**.

`CONFIRMADO`: OC97–OC112 são executadas integralmente por **Rennan**, incluindo
backend, banco, frontend, testes e documentação necessários em cada ocorrência.

`CONFIRMADO`: multiempresa/multitenancy **não faz parte da v1.2.0**.

## Compatibilidade com a futura integração CoreFlow

A v1.2.0 deve continuar plenamente utilizável sem CoreFlow. Entretanto, as áreas
administrativas não podem criar dependências que obriguem o LoadX a manter um
segundo control plane quando a integração futura acontecer.

Fronteira definida para o alvo integrado:

- **CoreFlow:** organização/tenant, identidade global, acesso à organização,
  licenciamento e entitlement do módulo;
- **LoadX:** domínio logístico, configurações operacionais, permissões logísticas,
  pedidos, frota, planejamento, viagens, entregas, evidências e integrações próprias.

As Issues #128, #129, #136, #137, #145 e #159 foram alinhadas para preservar o
modo standalone atual e, ao mesmo tempo, impedir acoplamento permanente de
identidade/empresa/licença ao domínio logístico.

`CONFIRMADO`: esta seção não autoriza SSO, tenant_id, CoreFlow ou qualquer mudança
de schema da v1.3.0 dentro da v1.2.0.

## Divisão oficial

| OC | Issue | Responsável | Área | Dependência principal |
|---|---:|---|---|---|
| OC79 | #122 | Rennan | Segurança / integrações | Nenhuma OC anterior |
| OC80 | #123 | Rennan | Entregas / evidências | Alinhar com OC79 |
| OC81 | #124 | Marlon | Frontend / comprovante | OC80 |
| OC82 | #125 | Marcelo | Integração / WhatsApp | OC79 |
| OC83 | #126 | Marcelo | Integração / webhook e mídia | OC79, OC80 e OC82 |
| OC84 | #127 | Marcelo | Integração / notificações | OC79 e OC82 |
| OC85 | #128 | Marlon | Frontend / configurações | Nenhuma OC anterior |
| OC86 | #129 | Marlon | Frontend / usuários | OC85 |
| OC87 | #130 | Rennan | Domínio / multi-caminhão | Exige ADR |
| OC88 | #131 | João | Algoritmo / multi-caminhão | OC87 |
| OC89 | #132 | Marlon | Frontend / multi-caminhão | OC87 e OC88 |
| OC90 | #133 | Marcelo | Operação / auditoria multi-caminhão | OC87 e OC88 |
| OC91 | #136 | Rennan | Configurações / empresa atual | OC85 |
| OC92 | #137 | Rennan | Conta / segurança | OC85 |
| OC93 | #138 | Marlon | Central operacional | OC90 e OC94 |
| OC94 | #139 | Marcelo | Exceções operacionais | OC87 e OC84 |
| OC95 | #140 | João | Busca por módulo | Nenhuma OC bloqueadora |
| OC96 | #141 | Marcelo | Relatórios / exportações | OC90 e OC94 |
| OC97 | #144 | Rennan | Auditoria / histórico | Nenhuma OC bloqueadora |
| OC98 | #145 | Rennan | Segurança de conta / MFA | OC92 |
| OC99 | #146 | Rennan | Clientes / endereços | Nenhuma OC bloqueadora |
| OC100 | #147 | Rennan | Frota / manutenção | Nenhuma OC bloqueadora |
| OC101 | #148 | Rennan | Frota / documentos | Nenhuma OC bloqueadora |
| OC102 | #149 | Rennan | Motoristas / documentos | Nenhuma OC bloqueadora |
| OC103 | #150 | Rennan | Notificações internas | OC84 |
| OC104 | #151 | Rennan | Cadastros / importação | Nenhuma OC bloqueadora |
| OC105 | #152 | Rennan | Cadastros / arquivamento | Nenhuma OC bloqueadora |
| OC106 | #153 | Rennan | Operação / agenda | OC93 |
| OC107 | #154 | Rennan | Busca global | OC95 |
| OC108 | #155 | Rennan | Administração / integrações | OC82 |
| OC109 | #156 | Rennan | Integrações / confiabilidade | OC84 |
| OC110 | #157 | Rennan | Arquivos / anexos | OC80 |
| OC111 | #158 | Rennan | Operação / linha do tempo | OC97 e OC93 |
| OC112 | #159 | Rennan | Segurança / permissões | OC86 |

## Diretriz transversal de permissões para todas as OCs

**Aprovado em 08/10/2026; implementação transversal pendente na OC112.**
`ADMIN` deve poder executar também as ações de `LOGISTICS_MANAGER` em
clientes, produtos, caminhões, motoristas, pedidos, planos e demais fluxos
gerenciais do LoadX, sem contornar regras/estados, vínculo de motorista ou
trilha de auditoria. `LOGISTICS_MANAGER` recebe as ações necessárias à
operação logística, **sem** poder de administrar usuários, credenciais de
terceiros, configuração institucional, catálogo de perfis e segurança.

**Orientação para o time:** OC85/86/91/92/99/100/101/102 e demais interfaces
devem usar este modelo-alvo ao desenhar navegação, ações e testes; porém,
enquanto a OC112 não integrar a mudança de autorização, a API e a interface
devem respeitar e declarar o RBAC *realmente vigente* (sem liberar apenas
botões nem antecipar permissão na API). A OC112 fará auditoria completa,
backend como autoridade, migração/compatibilidade e testes regressivos.
A hierarquia do ADMIN é interna ao LoadX; não representa SUPERADMIN nem
entitlement da plataforma CoreFlow.

## Frentes da versão

### Administração, conta e segurança
- OC85–OC86: Configurações e gestão de usuários do modo standalone, isoladas do domínio logístico.
- OC91–OC92: dados institucionais, perfil, senha e sessões do modo standalone, sem criar uma segunda fronteira de tenant.
- OC97–OC98: auditoria e segurança de conta; recuperação/MFA devem permanecer delegáveis a identidade externa no futuro.
- OC112: perfis e permissões **logísticas**, separando entitlement de plataforma de autorização interna do módulo.

### Comunicação, evidências e confiabilidade
- OC79–OC84: segurança externa, evidências, WhatsApp, webhook e notificações reais.
- OC103: central de notificações dentro do sistema.
- OC108: painel administrativo de saúde das integrações.
- OC109: fila/outbox, retentativas e reprocessamento.
- OC110: anexos e documentos operacionais.

`CONFIRMADO`: a implementação da OC79 na Issue #122 fornece apenas a fronteira
interna de segurança/idempotência. Contrato de consumo em
[external_commands](../../../backend/app/modules/external_commands/README.md);
decisão proposta na [ADR-026](../../decisions/ADR-026-seguranca-comandos-externos.md).
OC82/OC83 precisam fornecer autenticidade e vínculo de ator confiáveis; OC84
envia depois do commit. Não há fornecedor, webhook, mídia, outbox ou UI na OC79.
`PENDENTE DE DEFINIÇÃO`: aprovação do PR/ADR; este registro não conclui a Issue.

### Planejamento e operação

`CONFIRMADO`: a base OC87 e os ports para OC88/OC89/OC90 estão no
[contrato multi-caminhão](../../../backend/app/modules/load_planning/distributions.md).
`RECOMENDAÇÃO`: [ADR-028](../../decisions/ADR-028-planejamento-multi-caminhao.md)
define cobertura, aprovação, cancelamento e integridade; revisão humana pendente.

- OC87–OC90: multi-caminhão de ponta a ponta.
- OC93–OC94: central operacional e exceções/reentrega/cancelamento.
- OC106: agenda operacional.
- OC111: linha do tempo unificada.

### Frota, motoristas e cadastros
- OC99: múltiplos endereços por cliente.
- OC100: manutenção e disponibilidade programada.
- OC101–OC102: documentos e vencimentos de caminhões e motoristas.
- OC104: importação em massa.
- OC105: arquivamento e reativação.

### Pesquisa e gestão
- OC95: busca e filtros server-side nos módulos.
- OC107: busca global.
- OC96: relatórios gerenciais e exportações.

## Ordem recomendada de execução

`RECOMENDAÇÃO`:

1. manter em paralelo as OCs já liberadas da v1.2.0;
2. Rennan pode iniciar OC97, OC99, OC100, OC101, OC102, OC104 e OC105 imediatamente;
3. após OC92, executar OC98;
4. após OC84, executar OC103;
5. após OC93, executar OC106;
6. após OC95, executar OC107;
7. após OC82, executar OC108; após OC84, executar OC109;
8. após OC80, executar OC110;
9. após OC97 e OC93, executar OC111;
10. após OC86, executar OC112;
11. concluir integração, regressão e documentação antes de preparar `versao/v1.2.0`.

## Decisões obrigatórias

- OC87: ADR do modelo multi-caminhão.
- OC94: estados e transições de exceção.
- OC98: ADR de MFA, recuperação e contingência, incluindo ownership standalone versus futuro identity provider/CoreFlow.
- OC109: estratégia de fila/outbox e política de retentativas.
- OC110: storage, tipos MIME, limites e retenção de anexos.
- OC112: catálogo de permissões logísticas, permissões não delegáveis e fronteira com entitlement de plataforma.

## Regras permanentes

- backend continua sendo a fonte de verdade da autorização;
- integração externa nunca escreve diretamente nas tabelas de domínio;
- histórico e auditoria são somente leitura para usuários finais;
- registros com histórico não são apagados fisicamente por padrão;
- arquivos e credenciais permanecem atrás de contratos seguros;
- busca, filtros e agregações relevantes são feitos no servidor;
- nenhum recurso futuro da v1.3.0 pode ser antecipado silenciosamente para a v1.2.0;
- identidade, empresa e licenciamento standalone permanecem concentrados em módulos administrativos/auth, sem acoplamento aos domínios logísticos;
- nenhum código da v1.2.0 pode depender de banco, secret ou sessão do CoreFlow;
- integrações futuras com CoreFlow deverão usar API/contratos explícitos e bancos separados.

## Fluxo Git

```text
branch da ocorrência -> desenvolvimento -> versao/v1.2.0 -> main
```

`CONFIRMADO`: branches e commits priorizam português.

## Gates

- [x] milestone `v1.2.0` criado;
- [x] Issues #122–#133, #136–#141 e #144–#159 vinculadas ao milestone;
- [ ] todas as Issues funcionais adicionadas ao Project `LoadX — Desenvolvimento`;
- [x] dependências registradas no planejamento e automação;
- [x] validação automática de PR e bot apontando para v1.2.0.
