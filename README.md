# LoadX

Sistema inteligente para otimização, planejamento e acompanhamento de cargas logísticas.

O **LoadX** é um projeto acadêmico desenvolvido por uma equipe de quatro integrantes. Seu objetivo é auxiliar empresas de transporte na organização de volumes dentro do baú de caminhões, buscando melhorar o aproveitamento do espaço, reduzir erros no carregamento e facilitar a comunicação entre responsáveis logísticos, conferentes e motoristas.

## Sobre o projeto

O sistema recebe as dimensões internas do baú do caminhão e as informações dos volumes que serão transportados, como:

* largura;
* altura;
* comprimento;
* peso;
* quantidade;
* possibilidade de rotação;
* possibilidade de empilhamento;
* fragilidade.

Com base nesses dados, o LoadX utiliza algoritmos de otimização tridimensional para encontrar uma disposição válida para os volumes.

O resultado do planejamento poderá ser visualizado em uma representação 3D do baú, exibindo a posição, orientação e sequência de carregamento de cada volume.

O sistema também acompanhará o processo de carregamento e entrega, permitindo atualizações de status, registro de ocorrências, geração de relatórios e comunicação com motoristas por meio do WhatsApp.

## Objetivo geral

Desenvolver um sistema inteligente capaz de planejar automaticamente a disposição de volumes em caminhões, melhorar o aproveitamento do espaço disponível e acompanhar o processo logístico desde o carregamento até a conclusão das entregas.

1. `AGENTS.md`
2. `docs/00-visao-produto.md`
3. `docs/01-escopo-mvp.md`
4. `docs/02-arquitetura.md`
5. `docs/03-modelo-dados.md`
6. `docs/04-regras-negocio.md`
7. `docs/05-contratos-api.md`
8. `docs/08-padroes-desenvolvimento.md`
9. `docs/09-guia-para-ia.md`
10. `docs/11-riscos-pendencias.md`

A primeira versão do LoadX deverá permitir:

* autenticação de usuários;
* cadastro de clientes;
* cadastro de motoristas;
* cadastro de caminhões;
* cadastro de produtos e volumes;
* criação de pedidos;
* seleção do caminhão para o transporte;
* cálculo da disposição dos volumes;
* validação das dimensões do baú;
* validação do peso máximo;
* validação de colisões entre volumes;
* teste das rotações permitidas;
* cálculo do percentual de ocupação;
* identificação dos volumes que não couberam;
* geração da sequência de carregamento;
* comparação básica e determinística de até 10 caminhões candidatos;
* explicação técnica de um plano persistido com IA ou fallback determinístico;
* visualização tridimensional da carga;
* acompanhamento do carregamento;
* atualização do status das entregas;
* registro de ocorrências;
* integração real ou simulada com WhatsApp;
* geração de relatórios em PDF.

## Tecnologias

### Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic
* Pydantic
* Pytest

### Frontend

* React
* TypeScript
* Vite
* React Router
* Axios
* Three.js
* React Three Fiber
* Zod

### Banco de dados

* PostgreSQL

### Infraestrutura

* Docker
* Docker Compose
* Git
* GitHub
* GitHub Projects
* GitHub Actions

### Integrações

* WhatsApp Business Cloud API
* API de Inteligência Artificial

## Arquitetura

O projeto utiliza uma arquitetura de monólito modular.

A aplicação será dividida em módulos internos, mas continuará sendo executada como um único sistema.

```text
Frontend React
      |
      | API REST
      v
Backend FastAPI
      |
      +-- Autenticação
      +-- Cadastros
      +-- Pedidos
      +-- Planejamento de carga
      +-- Otimização 3D
      +-- Carregamento
      +-- Viagens e entregas
      +-- Ocorrências
      +-- WhatsApp
      +-- Relatórios
      |
      v
PostgreSQL
```

## Estrutura do projeto

```text
loadx-smart-logistics/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── integrations/
│   │   ├── modules/
│   │   └── shared/
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── services/
│   │   ├── tests/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── docs/
│   ├── decisions/
│   ├── diagrams/
│   └── prompts/
│
├── infra/
├── .github/
├── AGENTS.md
├── CLAUDE.md
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md
```

## Convenções do cálculo tridimensional

O sistema utilizará centímetros para dimensões e quilogramas para peso.

O sistema de coordenadas será:

```text
X = largura do baú
Y = altura do baú
Z = comprimento do baú
```

A origem das coordenadas será o canto frontal esquerdo do piso do baú.

```text
Origem: X = 0, Y = 0, Z = 0
```

Cada volume planejado deverá possuir:

```json
{
  "volume_id": 1,
  "posicao_x": 0,
  "posicao_y": 0,
  "posicao_z": 0,
  "largura": 60,
  "altura": 50,
  "comprimento": 40,
  "rotacao": "XYZ",
  "ordem_carregamento": 1
}
```

## Papel da Inteligência Artificial

A Inteligência Artificial será utilizada como apoio ao sistema.

Ela poderá:

* interpretar mensagens enviadas pelos motoristas;
* identificar a intenção de uma mensagem;
* classificar ocorrências;
* gerar explicações técnicas sobre um planejamento já calculado;
* resumir resultados e relatórios.

As validações de espaço, dimensões, peso e colisões serão realizadas por algoritmos determinísticos.

A IA não será responsável por decidir matematicamente se um volume cabe ou não no caminhão.

## Fluxo principal

```text
Cadastro do caminhão
        |
Cadastro dos produtos
        |
Criação do pedido
        |
Seleção do caminhão
        |
Execução do algoritmo
        |
Geração das posições
        |
Visualização 3D
        |
Início do carregamento
        |
Conferência da carga
        |
Liberação do veículo
        |
Início da viagem
        |
Atualização dos status
        |
Registro de ocorrências
        |
Conclusão das entregas
        |
Geração do relatório
```

## Divisão da equipe

### Desenvolvedor 1: Backend e banco de dados

Responsável por:

* configuração do FastAPI;
* PostgreSQL;
* migrations;
* autenticação;
* usuários;
* clientes;
* motoristas;
* caminhões;
* produtos;
* pedidos;
* viagens;
* contratos da API.

### Desenvolvedor 2: Algoritmo e otimização

Responsável por:

* cálculo das dimensões;
* expansão dos volumes;
* rotações permitidas;
* validação dos limites;
* detecção de colisões;
* controle de peso;
* heurística de posicionamento;
* cálculo de ocupação;
* sequência de carregamento;
* comparação básica entre caminhões e preparação dos dados explicáveis do plano;
* testes matemáticos.

### Desenvolvedor 3: Frontend e visualização 3D

Responsável por:

* interface do sistema;
* dashboard;
* telas de cadastro;
* criação de pedidos;
* tela de planejamento;
* consumo da API;
* visualização do baú;
* renderização dos volumes;
* animação do carregamento.

### Desenvolvedor 4: Operação, integrações e qualidade

Responsável por:

* controle de carregamento;
* entregas;
* ocorrências;
* integração com WhatsApp;
* relatórios em PDF;
* testes de integração;
* Docker;
* documentação;
* preparação da demonstração.

## Configuração do ambiente

### Requisitos

Antes de iniciar, instale:

* Git
* Docker
* Docker Compose

### Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/loadx-smart-logistics.git
cd loadx-smart-logistics
```

### Configurar variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis necessárias no arquivo `.env`.

Exemplo:

```env
APP_ENV=local
DATABASE_URL=postgresql+psycopg://loadx:loadx_local@db:5432/loadx
SECRET_KEY=troque-esta-chave-no-env-local
LOADX_SECRETS_DIR=
PASSWORD_BLOCKLIST_PATH=
WHATSAPP_TOKEN=
OPENAI_API_KEY=
```

Nunca envie o arquivo `.env` para o GitHub.

`APP_ENV` aceita somente `local` ou `production`. Use `local` no desenvolvimento. Em produção, configure `APP_ENV=production` para não expor `/docs`, `/redoc`, `/docs/oauth2-redirect` e `/openapi.json`. Se a variável não for informada, o backend assume `production` por segurança.

`CONFIRMADO`: em produção, o backend recusa iniciar com `SECRET_KEY` fraca ou
com menos de 32 caracteres, `DATABASE_URL` local padrão ou origem CORS curinga.
Conforme D18, produção autentica pelo cookie `__Host-loadx_session`; o ambiente
local HTTP usa `loadx_session` para não violar os requisitos do prefixo
reservado.

### Iniciar o sistema

```bash
docker compose up --build
```

Para executar em segundo plano:

```bash
docker compose up -d --build
```

O serviço `migrate` aplica `alembic upgrade head` depois que o PostgreSQL fica
saudável. Backend e frontend só iniciam após a migration terminar com sucesso.
As portas publicadas pelo Compose aceitam conexão apenas da máquina local por
padrão; `POSTGRES_PORT`, `BACKEND_PORT` e `FRONTEND_PORT` permitem trocar as
portas sem editar o arquivo.

### Encerrar o sistema

```bash
docker compose down
```

Para remover também os dados locais do banco:

```bash
docker compose down -v
```

### Referência de produção

`compose.production.yaml` é separado do ambiente local. Ele exige domínio, duas
URLs PostgreSQL e uma chave secreta fornecidos pelo ambiente seguro do host:

```bash
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml up -d --build --wait
```

Leia `infra/production/README.md` antes de executar. `CONFIRMADO`: somente Caddy
publica 80/443; backend permanece privado e recebe proxy headers somente do IP
fixo do Caddy. `RISCO IDENTIFICADO`: essa referência não substitui backup,
restauração, observabilidade e validação no domínio real.

## Endereços locais

Depois de iniciar os serviços:

```text
Frontend:
http://localhost:5173

Backend:
http://localhost:8000

Documentação da API:
http://localhost:8000/docs

Verificação da API:
http://localhost:8000/health

Prontidão da API:
http://localhost:8000/ready
```

A documentação da API acima existe somente com `APP_ENV=local`.

`/health` confirma apenas que o processo está em execução. `/ready` retorna
sucesso somente com PostgreSQL acessível e a revisão Alembic no head.

## Banco de dados

Cada desenvolvedor deverá utilizar um PostgreSQL local executado pelo Docker Compose.

As alterações estruturais do banco deverão ser feitas com migrations do Alembic.

Não devem ser realizadas alterações permanentes diretamente pelo pgAdmin.

### Aplicar migrations

```bash
docker compose exec backend alembic upgrade head
```

O Compose aplica as migrations automaticamente no início. O comando manual
continua disponível para manutenção. O endpoint `/ready` permanece somente
leitura e nunca aplica migrations; essa responsabilidade pertence ao serviço
isolado `migrate`.

### Criar uma nova migration

```bash
docker compose exec backend alembic revision --autogenerate -m "cria tabela de produtos"
```

## Organização das branches

O projeto utiliza as seguintes branches principais:

```text
main
develop
```

A branch `main` contém apenas versões estáveis.

A branch `develop` contém a versão integrada em desenvolvimento.

Cada ocorrência deve ser desenvolvida em uma branch própria.

Exemplo:

```text
feature/OC-01-configurar-backend
feature/OC-12-modelos-otimizador
feature/OC-20-visualizacao-3d
feature/OC-30-integracao-whatsapp
```

### Criar uma branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/OC-01-configurar-backend
```

### Enviar alterações

```bash
git add .
git commit -m "feat: configura estrutura inicial do backend"
git push origin feature/OC-01-configurar-backend
```

Depois disso, deverá ser aberto um Pull Request para a branch `develop`.

## Padrão de commits

Utilize mensagens claras:

```text
feat: adiciona cadastro de caminhões
fix: corrige cálculo de ocupação
test: adiciona testes de colisão
docs: atualiza modelo do banco
refactor: reorganiza serviço de planejamento
chore: atualiza dependências
```

## Critério de conclusão

Uma ocorrência será considerada concluída quando:

* o código estiver implementado;
* os critérios de aceitação forem atendidos;
* os testes estiverem funcionando;
* a documentação estiver atualizada;
* o código tiver sido enviado para uma branch;
* o Pull Request tiver sido revisado;
* a integração com a branch `develop` estiver funcionando.

## Documentação para ferramentas de IA

Antes de gerar ou alterar código, ferramentas de IA devem consultar:

```text
AGENTS.md
CLAUDE.md
.github/copilot-instructions.md
docs/09-guia-para-ia.md
README.md do módulo alterado
```

As ferramentas não devem:

* alterar a arquitetura sem justificativa;
* criar novas tecnologias sem aprovação;
* modificar contratos da API silenciosamente;
* alterar o sistema de coordenadas;
* misturar centímetros e metros;
* usar IA generativa para validar colisões;
* implementar funcionalidades fora do MVP;
* acessar diretamente tabelas de outro módulo sem utilizar os serviços definidos.

## Funcionalidades futuras

Após a conclusão do MVP, poderão ser adicionadas:

* leitura de QR Code;
* reconhecimento de volumes por câmera;
* acompanhamento por GPS;
* roteirização inteligente;
* análise de peso por eixo;
* comparação automática avançada entre veículos, sujeita a regras futuras de ranking e escolha;
* previsão de atrasos;
* aplicativo móvel;
* realidade aumentada;
* aprendizado com viagens anteriores;
* integração com sistemas ERP.

`CONFIRMADO`: a comparação básica de 2 a 10 caminhões pertence ao MVP, reutiliza
integralmente a mesma engine determinística e retorna os resultados sem persistir
plano, ranquear, pontuar ou escolher vencedor. A comparação automática avançada
permanece uma evolução futura.

`CONFIRMADO`: a explicação do plano no MVP consome somente dados técnicos de um
plano persistido. A IA não aprova, recalcula ou modifica o resultado; timeout,
indisponibilidade ou resposta inválida do provider usam fallback determinístico.

## Status do projeto

Projeto em fase inicial de desenvolvimento.

```text
Planejamento: concluído
Estrutura inicial: concluída
Backend: em desenvolvimento
Frontend: em desenvolvimento
Algoritmo: implementado até a OC20
Integrações: não iniciadas
```

## Projeto acadêmico

Este projeto está sendo desenvolvido como atividade acadêmica por estudantes de Engenharia de Software.

O objetivo é aplicar conceitos de:

* engenharia de requisitos;
* desenvolvimento web;
* banco de dados;
* arquitetura de software;
* algoritmos de otimização;
* Inteligência Artificial;
* trabalho em equipe;
* controle de versão;
* testes;
* documentação.

## Licença

Este projeto possui finalidade acadêmica.

A definição de uma licença de código aberto poderá ser realizada posteriormente.
