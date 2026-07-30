# Instruções para agentes de IA

Este arquivo é a fonte principal de contexto para qualquer IA que ajude a programar o LoadX.

## Antes de qualquer alteração

1. Leia o `README.md` da raiz.
2. Leia os documentos `docs/00` até `docs/05`.
3. Leia `docs/08-padroes-desenvolvimento.md`.
4. Leia `docs/09-guia-para-ia.md`.
5. Leia o `README.md` da pasta que será alterada.
6. Verifique ADRs relacionadas em `docs/decisions/`.
7. Verifique se a alteração pertence a uma ocorrência aprovada.

## Marcadores obrigatórios de incerteza

Use estes marcadores sempre que documentar ou reportar algo:

- `CONFIRMADO`: existe no código, documentação oficial, ADR ou documento-base aprovado.
- `RECOMENDAÇÃO`: padrão técnico proposto para manter consistência, ainda sem ADR própria.
- `SUPOSIÇÃO TÉCNICA`: inferência feita a partir da estrutura atual.
- `PENDENTE DE DEFINIÇÃO`: a equipe ainda precisa detalhar.
- `DECISÃO NECESSÁRIA`: exige escolha explícita da equipe antes de implementar.
- `RISCO IDENTIFICADO`: pode causar retrabalho, inconsistência ou falha operacional.

Não apresente suposições como decisões aprovadas.

## Escopo do MVP

Inclui caminhões, produtos, clientes, motoristas, pedidos, planejamento 3D, carregamento, entregas, ocorrências, relatórios e WhatsApp simulado ou controlado.

Não inclui paletes, GPS real, câmera, OpenCV, MDF-e, roteirização externa, previsão meteorológica, telemetria ou treinamento de modelo próprio.

## Convenções obrigatórias

- Dimensões internas e dos produtos são armazenadas em centímetros.
- Peso é armazenado em quilogramas.
- Coordenadas usam `x = largura`, `y = altura`, `z = comprimento`.
- A origem `(0, 0, 0)` fica no piso, no canto frontal esquerdo do baú.
- IDs são UUID, salvo decisão registrada em ADR.
- Datas e horários são armazenados em UTC.
- Nomes de código, tabelas, rotas e campos ficam em inglês.
- Textos de interface e documentação podem ficar em português.
- Endpoints públicos usam kebab-case no caminho e JSON em snake_case.

## Arquitetura

- Monólito modular.
- Rotas HTTP apenas validam entrada, chamam serviços e formatam respostas.
- Regras de negócio ficam em `service.py` ou `domain/`.
- Acesso ao banco fica em `repository.py`.
- Models SQLAlchemy ficam no módulo dono da tabela.
- Schemas Pydantic ficam em `schemas.py`.
- Integrações externas ficam atrás de interfaces/adapters em `app/integrations`.
- Módulos não acessam diretamente tabelas internas de outros módulos sem service público.

## Procedimento para novas funcionalidades

1. Confirme a ocorrência, objetivo e critérios de aceite.
2. Leia os contratos e regras relacionados em `docs`.
3. Use a menor mudança coerente com o módulo dono.
4. Crie somente arquivos necessários para a ocorrência atual.
5. Adicione ou atualize testes da regra de negócio ou do contrato alterado.
6. Atualize documentação quando mudar arquitetura, banco, regras, fluxos, API ou padrão.
7. Informe pendências quando algo depender de decisão da equipe.

## Banco e migrations

- A estrutura oficial do PostgreSQL vem de migrations Alembic.
- Não altere banco manualmente como solução definitiva.
- Não crie tabela, coluna, índice ou constraint fora de `docs/03-modelo-dados.md`.
- Tabelas usam plural em snake_case.
- Chaves primárias usam `id`.
- Chaves estrangeiras usam `<tabela_singular>_id`.
- Colunas de dimensão terminam em `_cm`.
- Colunas de peso terminam em `_kg`.
- Datas e horários terminam em `_at`.
- Dados de seed devem ser fictícios.

## Regras para geração de código

- Faça mudanças pequenas e focadas.
- Não invente campos, endpoints, estados, tecnologias ou regras de negócio.
- Não crie dependência externa sem justificar e atualizar os arquivos de dependências.
- Não grave segredos, tokens ou URLs privadas.
- Não use dados pessoais reais em seeds ou testes.
- Adicione ou atualize testes para toda regra de negócio.
- Nunca marque uma ocorrência como concluída sem teste mínimo.
- Não altere a estrutura principal do projeto sem aprovação.
- Não substitua padrões existentes por preferência pessoal.

## Otimização de carga

- A IA generativa não posiciona volumes diretamente.
- O otimizador deve ser determinístico, testável e reproduzível.
- Uma solução inválida nunca pode ser aceita para melhorar a porcentagem de ocupação.
- Colisão, limites, rotação, peso e apoio devem ser validados por código.
- O frontend apenas exibe coordenadas aprovadas pelo backend.

## O que não pode mudar sem aprovação

- Escopo do MVP.
- Convenções de unidade e coordenadas.
- Prefixo e contratos públicos da API.
- Tecnologia principal de backend, frontend ou banco.
- Estratégia de monólito modular.
- Modelo de dados aprovado.
- Regras críticas do otimizador.
- Integração real com provedor externo paga ou com credenciais.

## Ao terminar uma tarefa

Informe:

1. arquivos alterados;
2. decisão tomada;
3. testes executados;
4. pendências ou riscos;
5. documentação atualizada.
