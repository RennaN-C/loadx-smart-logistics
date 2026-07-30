# Visão do produto

## Problema

`CONFIRMADO`: a montagem de cargas costuma depender de experiência manual, tentativa e erro e comunicação fragmentada. Isso pode desperdiçar espaço, aumentar retrabalho e dificultar o acompanhamento da operação.

## Solução

`CONFIRMADO`: o LoadX organiza volumes dentro do baú de um caminhão, retorna posições tridimensionais, orienta a ordem de carregamento e acompanha os principais estados até a entrega.

## Objetivo do MVP

`CONFIRMADO`: demonstrar um fluxo completo e integrado, do cadastro ao relatório, com visualização 3D coerente com as coordenadas calculadas pelo backend.

O MVP deve permitir:

- cadastrar caminhões, produtos, clientes e motoristas;
- criar pedidos com itens e quantidades;
- selecionar caminhão e pedidos para planejamento;
- calcular uma disposição válida dos volumes;
- salvar coordenadas e ordem de carregamento;
- exibir a carga em 3D;
- acompanhar carregamento e entrega;
- registrar ocorrências;
- interpretar mensagens controladas do motorista;
- gerar relatório simples em PDF.

## Usuários do MVP

- Administrador: gerencia usuários e dados básicos.
- Responsável logístico: cria pedidos, seleciona caminhões e aprova planos.
- Conferente: acompanha e confirma o carregamento.
- Motorista: consulta entrega, atualiza status e registra ocorrência.

## Diferencial

`CONFIRMADO`: o núcleo é um otimizador geométrico determinístico. A IA é usada como apoio para interpretar mensagens e explicar resultados, nunca para substituir validações físicas.

## Limites do produto

`CONFIRMADO`: o LoadX não é, no MVP, um sistema de roteirização externa, telemetria, previsão climática, leitura fiscal, aplicativo móvel nativo ou reconhecimento automático por câmera.

`RECOMENDAÇÃO`: qualquer funcionalidade futura deve entrar primeiro como ocorrência aprovada e, quando alterar arquitetura, contrato, unidade, integração ou regra relevante, receber ADR.

## Fonte de verdade

`CONFIRMADO`: a documentação oficial do projeto fica em `docs`, nas ADRs em `docs/decisions` e nos guias `AGENTS.md` da raiz e das áreas.

`CONFIRMADO`: o documento-base anexado com divisão em 4 desenvolvedores foi usado para complementar responsabilidades, ocorrências e requisitos, mas os nomes técnicos seguem a convenção já aprovada de código e banco em inglês.
