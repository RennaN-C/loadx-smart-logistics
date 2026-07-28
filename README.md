# LoadX

Sistema inteligente para planejamento tridimensional de cargas, acompanhamento do carregamento e controle básico de entregas.

## Objetivo do MVP

O MVP deve permitir:

1. cadastrar caminhões, produtos, clientes e motoristas;
2. criar pedidos com volumes;
3. selecionar um caminhão;
4. calcular uma disposição válida dos volumes;
5. salvar coordenadas e ordem de carregamento;
6. visualizar a carga em 3D;
7. acompanhar carregamento e entrega;
8. registrar ocorrências;
9. interpretar mensagens controladas do motorista;
10. gerar um relatório simples.

## Tecnologias oficiais

- Backend: Python 3.12, FastAPI, SQLAlchemy e Alembic.
- Banco: PostgreSQL 16.
- Frontend: React, TypeScript e Vite.
- Visualização: React Three Fiber e Three.js.
- Infraestrutura local: Docker Compose.
- Testes: Pytest, Vitest e Testing Library.
- Integrações: provedor de IA por adaptador e WhatsApp inicialmente simulado.

## Primeiros passos

1. Copie `.env.example` para `.env`.
2. Instale Docker Desktop.
3. Execute `docker compose up --build`.
4. Backend: `http://localhost:8000`.
5. Swagger: `http://localhost:8000/docs`.
6. Frontend: `http://localhost:5173`.

## Documentação obrigatória

Antes de programar, humanos e agentes de IA devem ler:

1. `AGENTS.md`
2. `docs/00-visao-produto.md`
3. `docs/01-escopo-mvp.md`
4. `docs/02-arquitetura.md`
5. `docs/03-modelo-dados.md`
6. `docs/04-regras-negocio.md`
7. `docs/05-contratos-api.md`
8. `docs/09-guia-para-ia.md`

## Regra principal

O algoritmo determinístico decide se a carga é válida. A IA pode interpretar mensagens e explicar resultados, mas não pode ignorar dimensões, peso, colisões ou restrições.
