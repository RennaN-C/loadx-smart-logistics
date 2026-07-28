# Instruções para agentes de IA

Este arquivo é a fonte principal de contexto para qualquer IA que ajude a programar o LoadX.

## Antes de alterar código

1. Leia o `README.md` da raiz.
2. Leia os documentos `docs/00` até `docs/05`.
3. Leia o `README.md` da pasta que será alterada.
4. Verifique se existe ADR relacionado em `docs/decisions/`.
5. Não implemente funcionalidades fora do MVP sem uma ocorrência aprovada.

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

## Arquitetura

- Monólito modular.
- Rotas HTTP apenas validam entrada, chamam serviços e formatam respostas.
- Regras de negócio ficam em services/domain.
- Acesso ao banco fica em repositories.
- Integrações externas ficam atrás de interfaces/adapters.
- Módulos não acessam diretamente tabelas internas de outros módulos sem service público.

## Regras para geração de código

- Faça mudanças pequenas e focadas.
- Não invente campos, endpoints ou estados fora da documentação.
- Não crie dependência externa sem justificar e atualizar os arquivos de dependências.
- Não grave segredos, tokens ou URLs privadas.
- Não use dados pessoais reais em seeds ou testes.
- Adicione ou atualize testes para toda regra de negócio.
- Atualize a documentação quando mudar contrato, regra ou arquitetura.
- Nunca marque uma ocorrência como concluída sem teste mínimo.

## Otimização de carga

- A IA generativa não posiciona volumes diretamente.
- O otimizador deve ser determinístico, testável e reproduzível.
- Uma solução inválida nunca pode ser aceita para melhorar a porcentagem de ocupação.
- Colisão, limites, rotação, peso e apoio devem ser validados por código.

## Ao terminar uma tarefa

Informe:

1. arquivos alterados;
2. decisão tomada;
3. testes executados;
4. pendências ou riscos;
5. documentação atualizada.
