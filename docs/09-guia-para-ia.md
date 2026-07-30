# Guia para usar IA no desenvolvimento

## Objetivo

Permitir que ChatGPT, Codex, Copilot, Claude ou outra IA compreenda o LoadX sem recriar a arquitetura a cada conversa.

`CONFIRMADO`: este guia complementa `AGENTS.md`; não substitui os documentos numerados nem ADRs.

## Arquivos que a IA deve consultar

Antes de programar:

1. `AGENTS.md`.
2. `README.md`.
3. `docs/00-visao-produto.md`.
4. `docs/01-escopo-mvp.md`.
5. `docs/02-arquitetura.md`.
6. `docs/03-modelo-dados.md`.
7. `docs/04-regras-negocio.md`.
8. `docs/05-contratos-api.md`.
9. `docs/08-padroes-desenvolvimento.md`.
10. README da pasta ou módulo afetado.
11. ADRs relacionadas em `docs/decisions`.

Antes de alterar banco:

- `docs/03-modelo-dados.md`.
- `backend/app/database/README.md`.
- `backend/migrations/README.md`.
- README do módulo dono.

Antes de alterar frontend:

- `frontend/AGENTS.md`.
- `frontend/README.md`.
- `frontend/src/README.md`.
- README da feature.

Antes de alterar backend:

- `backend/AGENTS.md`.
- `backend/README.md`.
- `backend/app/README.md`.
- README do módulo.

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
Implemente a OC15 no módulo load_planning.
Leia AGENTS.md, docs/04-regras-negocio.md e o README do módulo.
Não altere o contrato da API.
Adicione testes para colisão e limites.
```

## Padrões obrigatórios

- Respeitar escopo do MVP.
- Preservar monólito modular.
- Manter nomes técnicos em inglês.
- Usar centímetros, quilogramas e UTC.
- Usar `x = largura`, `y = altura`, `z = comprimento`.
- Seguir camadas `router -> schemas -> service -> repository -> model`.
- Criar apenas arquivos necessários para a ocorrência atual.
- Atualizar documentação quando mudar arquitetura, banco, regras, fluxos, API ou padrões.
- Usar marcadores `CONFIRMADO`, `RECOMENDAÇÃO`, `SUPOSIÇÃO TÉCNICA`, `PENDENTE DE DEFINIÇÃO`, `DECISÃO NECESSÁRIA` e `RISCO IDENTIFICADO` quando houver incerteza.

## Forma correta de implementar novas funcionalidades

1. Confirmar a ocorrência e critérios de aceite.
2. Localizar o módulo dono.
3. Ler contratos, regras e README do módulo.
4. Verificar se já existe arquivo ou padrão equivalente.
5. Atualizar documentação primeiro quando a mudança alterar contrato, regra, banco ou arquitetura.
6. Implementar service/domain antes de expor rota quando houver regra de negócio.
7. Adicionar repository apenas quando houver persistência.
8. Registrar router no agregador somente quando o endpoint estiver testável.
9. Criar testes mínimos que comprovem a regra ou o fluxo.
10. Relatar arquivos alterados, decisão tomada, testes e pendências.

## Como criar ou alterar tabelas e migrations

1. Verificar se a tabela/coluna já está prevista em `docs/03-modelo-dados.md`.
2. Se não estiver, atualizar `docs/03` e marcar o status correto.
3. Criar ou atualizar model SQLAlchemy no módulo dono.
4. Criar migration Alembic.
5. Garantir PK, FK, índices, constraints e nomes conforme `docs/03` e `docs/08`.
6. Adicionar teste mínimo de repository, API ou regra afetada.
7. Não alterar banco manualmente como solução definitiva.

`PENDENTE DE DEFINIÇÃO`: comando oficial de Alembic ainda deve ser documentado quando a configuração inicial for implementada.

## Comportamentos proibidos

- Criar novos módulos sem necessidade.
- Criar outra estrutura de documentação.
- Duplicar guia existente em vez de atualizar o local correto.
- Inventar requisitos, tabelas, campos, endpoints, estados, tecnologias ou regras.
- Alterar nomes de campos unilateralmente.
- Adicionar bibliotecas por conveniência.
- Colocar regras geométricas críticas no frontend.
- Usar IA generativa como validador da carga.
- Aprovar plano inválido por ganho de ocupação.
- Acessar banco diretamente a partir de integrações externas.
- Criar credenciais fictícias dentro do código.
- Usar dados pessoais reais em seeds, testes ou exemplos.
- Afirmar que testes passaram sem executá-los.
- Apagar mudanças de outro colaborador sem pedido explícito.

## O que a IA não pode mudar sem aprovação

- Escopo do MVP.
- Convenções de unidades e coordenadas.
- Estratégia de monólito modular.
- Tecnologias oficiais.
- Modelo de dados aprovado.
- Prefixo e formato dos contratos públicos.
- Regras críticas do otimizador.
- Fluxo de autenticação e permissões.
- Integração real com WhatsApp, IA paga ou qualquer serviço externo com credenciais.

## Formato de entrega esperado da IA

- Resumo da solução.
- Arquivos criados ou alterados.
- Decisão tomada.
- Testes executados.
- Riscos e limitações.
- Pendências de definição.
- Documentação atualizada.

## Revisão por IA

Ao revisar código, priorizar:

- violação de regra de negócio;
- divergência de contrato da API;
- quebra da arquitetura modular;
- falta de teste;
- risco de segurança;
- dados reais ou segredos;
- escopo fora do MVP;
- nomenclatura fora do padrão.

Findings devem citar arquivo e linha quando possível.
