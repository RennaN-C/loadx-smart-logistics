# Divisão da equipe

## Desenvolvedor 1: backend e dados

Responsável por autenticação, banco, migrations, caminhões, produtos, clientes, motoristas, pedidos e contratos da API.

Pastas principais:

- `backend/app/core`
- `backend/app/database`
- `backend/app/modules/auth`
- `backend/app/modules/users`
- `backend/app/modules/trucks`
- `backend/app/modules/products`
- `backend/app/modules/customers`
- `backend/app/modules/drivers`
- `backend/app/modules/orders`

## Desenvolvedor 2: planejamento e algoritmo

Responsável pelo modelo de entrada, expansão dos volumes, rotações, posicionamento, colisões, peso, ocupação e testes do otimizador.

Pastas principais:

- `backend/app/modules/load_planning`
- `backend/tests/unit/load_planning`

## Desenvolvedor 3: frontend e 3D

Responsável pelas telas, serviços HTTP, componentes compartilhados, estado da aplicação e visualização tridimensional.

Pastas principais:

- `frontend/src/app`
- `frontend/src/components`
- `frontend/src/features`
- `frontend/src/services`

## Desenvolvedor 4: operação, integrações e qualidade

Responsável por carregamento, viagens, entregas, ocorrências, relatórios, provider mock de WhatsApp/IA, testes integrados e Docker.

Pastas principais:

- `backend/app/modules/loading`
- `backend/app/modules/deliveries`
- `backend/app/modules/occurrences`
- `backend/app/modules/reports`
- `backend/app/integrations`
- `backend/tests/integration`
- `infra`

## Trabalho compartilhado

- decisões arquiteturais;
- revisão de Pull Requests;
- documentação;
- testes ponta a ponta;
- apresentação;
- manutenção do ambiente staging.
