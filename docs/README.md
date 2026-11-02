# Documentação do LoadX

**Versão publicada:** [v1.2.0](https://github.com/RennaN-C/loadx-smart-logistics/releases/tag/v1.2.0) (26/10/2026).

Esta pasta reúne **documentação ativa**, **planejamento histórico**, **decisões arquiteturais** e **evidências de teste**. O registro de uma ocorrência antiga não significa que ela permaneça aberta.

## Onde encontrar cada assunto

| Assunto | Referência |
| --- | --- |
| Visão geral e início rápido | [README principal](../README.md) |
| Instalação, CI, execução e diagnóstico | [Guia de ambientes](13-guia-execucao-ambientes.md) |
| Produto e requisitos de origem | [Visão do produto](00-visao-produto.md) e [escopo inicial](01-escopo-mvp.md) |
| Arquitetura, dados, contratos, regras e fluxos | [Arquitetura](02-arquitetura.md), [dados](03-modelo-dados.md), [regras](04-regras-negocio.md), [API](05-contratos-api.md) e [fluxo](06-fluxo-operacional.md) |
| Contribuição e agentes | [Padrões](08-padroes-desenvolvimento.md), [guia para IA](09-guia-para-ia.md), [CONTRIBUTING](../CONTRIBUTING.md), [AGENTS](../AGENTS.md) |
| Releases e próximos ciclos | [Roadmap canônico](planejamento/roadmap-versoes.md), [Changelog](../CHANGELOG.md), [notas da v1.2.0](releases/v1.2.0.md) e [notas da v1.3.0](releases/v1.3.0.md) |
| Qualidade, riscos e histórico de aceite | [Riscos](11-riscos-pendencias.md), [registro de publicação](releases/v1.2.0-readiness.md), `evidencias/`, `validacoes/` |
| Decisões arquiteturais | [ADRs](decisions/README.md) |

## Versões

- **Versões anteriores publicadas:** v1.0.0 (fundação), v1.1.0 (maturidade operacional), v1.2.0 (administração e multi-caminhão).
- **Código desta versão:** **v1.3.0 — Loxi e Experiência Inteligente** ([PR #388](https://github.com/RennaN-C/loadx-smart-logistics/pull/388)). Confirmar publicação nas [Releases oficiais](https://github.com/RennaN-C/loadx-smart-logistics/releases); não equivale a deploy externo.
- **Planejamento histórico:** [v1.1.0](planejamento/v1.1.0/00-visao-geral.md) e [v1.2.0](planejamento/v1.2.0/00-visao-geral.md). O histórico mantém atribuições e dependências como foram planejadas.
- **Próximo ciclo proposto:** v1.4.0 — multiempresa e integração por contratos com CoreFlow. **Não** está automaticamente autorizado para implementação. Escala de 1.000+ volumes, tipos de embalagem, ações autorizadas do Loxi e estabilidade são backlog transversal de **versão a definir**.

## Histórico e limpeza segura

Os documentos `07-divisao-equipe.md`, `10-roadmap-inicial.md`, `12-ocorrencias-propostas-backend.md`, `decisoes-equipe-backend.txt` e `referencia-arquivo-original.md` preservam decisões e material acadêmico anterior. São arquivos históricos, não versões concorrentes do roadmap.

`evidencias/`, `validacoes/` e `usabilidade/` mantêm capturas, relatórios, roteiros e testes associados a revisões específicas. Não apagar evidências apenas por serem antigas. `decisions/` guarda ADRs e `prompts/` guarda modelos auxiliares.

Arquivos temporários como `.tmp/`, `node_modules/`, `dist/`, caches, ambientes virtuais e logs devem permanecer ignorados pelo Git. Antes de excluir qualquer arquivo versionado, conferir links, testes, CI, módulos que o utilizam e relevância histórica.

**Regra:** preferir atualizar a documentação canônica a criar outro arquivo com o mesmo assunto. Manutenção pós-release não altera o conteúdo de uma tag publicada.
