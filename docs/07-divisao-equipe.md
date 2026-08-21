# Divisão da equipe

`CONFIRMADO`: o projeto será desenvolvido por 4 desenvolvedores com apoio de IA no VS Code/Codex.

`CONFIRMADO`: a divisão abaixo consolida a estrutura atual do repositório e o documento-base anexado `LoadX_Divisao_4_Desenvolvedores_Ocorrencias.txt`.

## Regras de trabalho por ownership

- Cada ocorrência deve ter um responsável primário.
- Mudanças em contrato público devem envolver backend e frontend.
- Mudanças em banco devem envolver o responsável por backend/dados.
- Mudanças no otimizador devem ter teste unitário determinístico.
- Mudanças em status, ocorrência, WhatsApp ou relatório devem envolver o responsável por operação/qualidade.
- Pull Requests precisam de pelo menos uma revisão de outro integrante.

## Desenvolvedor 1: backend, banco e regras do sistema

Responsável por autenticação, banco, migrations, usuários, caminhões, motoristas, clientes, produtos, pedidos, viagens, entregas e histórico de status.

Pastas principais:

- `backend/app/core`.
- `backend/app/database`.
- `backend/app/api`.
- `backend/app/modules/auth`.
- `backend/app/modules/users`.
- `backend/app/modules/trucks`.
- `backend/app/modules/products`.
- `backend/app/modules/customers`.
- `backend/app/modules/drivers`.
- `backend/app/modules/orders`.
- `backend/app/modules/deliveries`.
- `backend/app/modules/status_history`.
- `backend/migrations`.
- `backend/tests/integration`.

Ocorrências do documento-base:

- [ ] `OC01`: configuração do projeto backend.
- [ ] `OC02`: criação e configuração do banco de dados.
- [ ] `OC03`: autenticação e controle de acesso.
- [ ] `OC04`: cadastro de caminhões.
- [ ] `OC05`: cadastro de motoristas.
- [ ] `OC06`: cadastro de clientes.
- [ ] `OC07`: cadastro de produtos e volumes.
- [ ] `OC08`: cadastro de pedidos.
- [ ] `OC09`: controle de viagens.
- [ ] `OC10`: histórico de status.

Entregas esperadas:

- [ ] API REST funcional.
- [ ] Migrations e banco funcionando.
- [ ] Autenticação e perfis.
- [ ] Cadastros principais.
- [ ] Controle de viagens, entregas e histórico.
- [ ] Endpoints documentados em `docs/05-contratos-api.md`.

## Desenvolvedor 2: otimização, cálculos e inteligência

Responsável pelo modelo de entrada, expansão dos volumes, cálculo de capacidade, rotações, posicionamento, colisões, apoio, peso, ocupação, comparação e explicação do plano.

Pastas principais:

- `backend/app/modules/load_planning`.
- `backend/app/modules/load_planning/optimizer`.
- `backend/tests/unit`.
- `backend/tests/unit/load_planning` quando a pasta existir.

Ocorrências do documento-base:

- [x] `OC11`: cálculo da capacidade do caminhão.
- [x] `OC12`: cálculo do volume dos produtos.
- [x] `OC13`: ordenação dos volumes.
- [x] `OC14`: rotação dos volumes.
- [x] `OC15`: posicionamento dos volumes.
- [x] `OC16`: validação de colisões.
- [x] `OC17`: validação de empilhamento.
- [x] `OC18`: controle de peso.
- [x] `OC19`: cálculo do aproveitamento.
- [x] `OC20`: sequência de carregamento.
- [ ] `OC21`: comparação entre caminhões.
- [ ] `OC22`: explicação do planejamento com IA.

Entregas esperadas:

- [ ] Algoritmo determinístico.
- [ ] Coordenadas dos volumes.
- [ ] Controle de colisão, limites, peso, rotação e apoio.
- [ ] Percentual de ocupação.
- [ ] Lista de volumes rejeitados.
- [ ] Sequência de carregamento.
- [ ] Testes unitários reproduzíveis.

## Desenvolvedor 3: frontend, dashboard e visualização 3D

Responsável pelas telas, serviços HTTP, componentes compartilhados, estado da aplicação e visualização tridimensional.

Pastas principais:

- `frontend/src/app`.
- `frontend/src/components`.
- `frontend/src/features`.
- `frontend/src/services`.
- `frontend/src/tests`.

Ocorrências do documento-base:

- [ ] `OC23`: configuração do frontend.
- [ ] `OC24`: tela de login.
- [ ] `OC25`: dashboard.
- [ ] `OC26`: tela de caminhões.
- [ ] `OC27`: tela de produtos.
- [ ] `OC28`: tela de clientes e motoristas.
- [ ] `OC29`: tela de pedidos.
- [ ] `OC30`: tela de planejamento.
- [ ] `OC31`: visualização 3D.
- [ ] `OC32`: interação com a visualização 3D.
- [ ] `OC33`: animação do carregamento.
- [ ] `OC34`: tela de acompanhamento.
- [ ] `OC35`: tela de indicadores e relatórios.

Entregas esperadas:

- [ ] Interface integrada com API.
- [ ] Dashboard e telas de cadastro.
- [ ] Tela de planejamento.
- [ ] Visualização 3D baseada no contrato da API.
- [ ] Animação de carregamento.
- [ ] Acompanhamento e indicadores visuais.
- [ ] Tratamento de loading, vazio e erro.

## Desenvolvedor 4: WhatsApp, ocorrências, relatórios e testes

Responsável por carregamento, ocorrências, notificações, relatórios, provider
mock de WhatsApp/IA, testes integrados, e2e, Docker e documentação operacional.
Colabora no fluxo de viagens e entregas consumindo o service público do módulo,
sem assumir os models, migration, regras de transição ou API pertencentes à
`OC09` do Desenvolvedor 1.

Pastas principais:

- `backend/app/modules/loading`.
- `backend/app/modules/occurrences`.
- `backend/app/modules/reports`.
- `backend/app/integrations`.
- `backend/tests/integration`.
- `backend/tests/e2e`.
- `frontend/src/features/loading-operation`.
- `frontend/src/features/deliveries`.
- `frontend/src/features/occurrences`.
- `frontend/src/features/reports`.
- `infra`.

Ocorrências do documento-base:

- [ ] `OC36`: configuração da integração com WhatsApp.
- [ ] `OC37`: comandos do motorista.
- [ ] `OC38`: interpretação de linguagem natural.
- [ ] `OC39`: atualização de status pelo WhatsApp.
- [ ] `OC40`: notificações automáticas.
- [ ] `OC41`: registro de ocorrências.
- [ ] `OC42`: envio de fotos.
- [ ] `OC43`: relatório de carregamento.
- [ ] `OC44`: relatório de viagem.
- [ ] `OC45`: geração de relatório em PDF.
- [ ] `OC46`: testes da API.
- [ ] `OC47`: testes do fluxo completo.
- [ ] `OC48`: documentação.

Entregas esperadas:

- [ ] Integração ou simulador do WhatsApp.
- [ ] Atualização de status.
- [ ] Controle de ocorrências.
- [ ] Notificações.
- [ ] Relatórios e PDF.
- [ ] Testes de API e fluxo completo.
- [ ] Documentação atualizada.

## Responsabilidades compartilhadas

Todos os desenvolvedores participam de:

- levantamento de requisitos;
- definição de regras de negócio;
- modelagem do sistema;
- revisão de código;
- testes finais;
- integração entre módulos;
- criação da apresentação;
- demonstração do sistema;
- documentação final.

## Regras de integração entre devs

- Backend e frontend combinam contrato em `docs/05` antes de implementar telas consumidoras.
- Banco e services públicos são combinados antes de outro módulo depender deles.
- Mudanças em nomes de tabela, campo ou endpoint exigem atualização simultânea em documentação, testes e código consumidor.
- A IA pode apoiar implementação, revisão e documentação, mas o responsável humano valida escopo, regra e teste.

`RISCO IDENTIFICADO`: o roadmap antigo usava outra numeração de ocorrências. A partir desta padronização, a numeração do documento-base (`OC01` a `OC48`) deve ser a referência para divisão de trabalho.
