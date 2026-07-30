# Documentação

Esta pasta concentra decisões oficiais do produto, arquitetura, dados, contratos, processo e uso de IA. Código não deve contradizer estes documentos.

## Ordem de leitura

- `00-visao-produto.md`: problema, usuários, objetivo e fonte de verdade.
- `01-escopo-mvp.md`: escopo, requisitos funcionais e não funcionais.
- `02-arquitetura.md`: componentes, camadas, tecnologias e responsabilidades por pasta.
- `03-modelo-dados.md`: entidades, tabelas, colunas, relações, chaves, índices e migrations.
- `04-regras-negocio.md`: regras obrigatórias, estados, ocorrências, WhatsApp, IA e relatórios.
- `05-contratos-api.md`: endpoints, formatos, erros, segurança de API e integrações.
- `06-fluxo-operacional.md`: jornadas principais do cadastro ao relatório.
- `07-divisao-equipe.md`: responsabilidade dos quatro integrantes e ocorrências `OC01` a `OC48`.
- `08-padroes-desenvolvimento.md`: Git, PR, nomenclatura, camadas, banco, testes, logs e segurança.
- `09-guia-para-ia.md`: como orientar agentes de programação.
- `10-roadmap-inicial.md`: sequência de sprints baseada no documento-base.
- `11-riscos-pendencias.md`: decisões necessárias, riscos, dúvidas e pendências.
- `decisions/`: registros de decisões arquiteturais.
- `diagrams/`: diagramas Mermaid, UML e banco.
- `prompts/`: modelos de prompt para IA.

## Regra de manutenção

Antes de criar um novo documento:

1. verifique se o assunto já está coberto em um guia existente;
2. atualize o arquivo existente quando ele for o local adequado;
3. crie novo guia somente quando não houver lugar apropriado;
4. mantenha a numeração e nomes em português usados nesta pasta;
5. registre incertezas com os marcadores definidos em `AGENTS.md`.
