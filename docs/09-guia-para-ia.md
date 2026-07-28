# Guia para usar IA no desenvolvimento

## Objetivo

Permitir que ChatGPT, Codex, Copilot, Claude ou outra IA compreenda o LoadX sem recriar a arquitetura a cada conversa.

## Contexto mínimo para toda tarefa

Ao pedir código, informe:

1. número da ocorrência;
2. módulo afetado;
3. critério de aceite;
4. arquivos relevantes;
5. contrato de entrada e saída;
6. testes esperados.

Exemplo:

```text
Implemente a OC-15 no módulo load_planning.
Leia AGENTS.md, docs/04-regras-negocio.md e o README do módulo.
Não altere o contrato da API.
Adicione testes para colisão e limites.
```

## Arquivos que a IA deve consultar

- `AGENTS.md` para regras gerais;
- `docs/01-escopo-mvp.md` para evitar escopo extra;
- `docs/04-regras-negocio.md` para validações;
- `docs/05-contratos-api.md` para integração;
- `README.md` do módulo para responsabilidades;
- ADRs para decisões permanentes.

## Comportamentos proibidos

- criar novos módulos sem necessidade;
- inventar requisitos;
- alterar nomes de campos unilateralmente;
- adicionar bibliotecas por conveniência;
- colocar regras geométricas no frontend;
- usar IA generativa como validador da carga;
- criar credenciais fictícias dentro do código;
- afirmar que testes passaram sem executá-los.

## Formato de entrega esperado da IA

- resumo da solução;
- arquivos criados ou alterados;
- código completo ou patch;
- testes executados;
- riscos e limitações;
- atualização documental necessária.
