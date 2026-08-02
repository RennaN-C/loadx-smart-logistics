<div align="center">

#  LOAD X

### Sistema Operacional Logístico Inteligente

Plataforma para gestão de operações logísticas, planejamento de cargas e futura aplicação de algoritmos de otimização.

<br>

![Status](https://img.shields.io/badge/STATUS-EM%20DESENVOLVIMENTO-000000?style=for-the-badge&logoColor=white)
![Equipe](https://img.shields.io/badge/EQUIPE-4%20DESENVOLVEDORES-000000?style=for-the-badge&logo=github&logoColor=white)
![Projeto](https://img.shields.io/badge/PROJETO-ACADÊMICO-000000?style=for-the-badge&logo=academia&logoColor=white)

<br>

![Python](https://img.shields.io/badge/PYTHON-3.12-000000?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-API-000000?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-DATABASE-000000?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/DOCKER-CONTAINERS-000000?style=for-the-badge&logo=docker&logoColor=white)

<br>

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📌 VISÃO GERAL

O **LOAD X** é uma plataforma desenvolvida para centralizar e organizar processos logísticos relacionados a clientes, motoristas, caminhões, produtos, pedidos e planejamento de cargas.

O sistema estabelece uma base operacional para empresas de transporte e distribuição, permitindo registrar os principais recursos envolvidos na operação, acompanhar pedidos e preparar os dados necessários para a futura otimização do carregamento dos veículos.

A proposta não se limita à criação de cadastros. O projeto está sendo estruturado para evoluir como uma plataforma modular, capaz de incorporar:

- Planejamento inteligente de cargas
- Validação de capacidade física dos veículos
- Controle de peso e volume
- Visualização tridimensional do carregamento
- Monitoramento das operações
- Integrações externas
- Relatórios para apoio à tomada de decisão

> O projeto encontra-se em desenvolvimento e ainda não está preparado para utilização em ambiente de produção.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 👥 INTEGRANTES

| Integrante | Participação |
|---|---|
| Rennan de Oliveira Cardoso | Desenvolvimento e organização do projeto |
| Marlon Myszka | Desenvolvimento |
| Marcelo Barbusa | Desenvolvimento |
| Joao Victor Weber | Desenvolvimento |

As responsabilidades são distribuídas de acordo com as etapas, módulos e necessidades técnicas do projeto.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📌 RESUMO DA AUTOMAÇÃO PROPOSTA

O LOAD X foi idealizado para reduzir a dependência de controles manuais e informações espalhadas durante o planejamento logístico.

A plataforma centraliza dados de:

- Clientes
- Motoristas
- Caminhões
- Produtos
- Pedidos
- Usuários
- Histórico de alterações
- Capacidade dos veículos
- Peso e dimensões dos produtos

A partir desses dados, o sistema poderá gerar planos de carregamento considerando as limitações reais de cada caminhão e os requisitos dos pedidos selecionados.

O objetivo futuro é permitir que algoritmos de otimização auxiliem na distribuição dos produtos dentro dos veículos, buscando melhorar o aproveitamento do espaço disponível e reduzir falhas operacionais.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## OBJETIVOS

- Centralizar as informações da operação logística
- Automatizar etapas repetitivas do planejamento
- Reduzir erros operacionais e inconsistências de dados
- Melhorar o aproveitamento do espaço dos caminhões
- Controlar peso, volume e dimensões das cargas
- Organizar pedidos, produtos, motoristas e veículos
- Fornecer uma base confiável para algoritmos de otimização
- Facilitar o acompanhamento das operações
- Apoiar gestores durante a tomada de decisão
- Manter histórico e rastreabilidade das alterações realizadas

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

##  FUNCIONALIDADES IMPLEMENTADAS

### Autenticação e autorização

- Autenticação utilizando token Bearer
- Consulta dos dados do usuário autenticado
- Controle de acesso por perfil
- Proteção dos endpoints da API
- Gerenciamento de usuários restrito ao perfil administrativo
- Proteção contra remoção ou desativação do último administrador ativo
- Processo de criação do primeiro administrador local

Perfis atualmente previstos:

| Perfil | Responsabilidade |
|---|---|
| `ADMIN` | Administração de usuários e acesso geral |
| `LOGISTICS_MANAGER` | Gerenciamento dos cadastros operacionais |
| `CHECKER` | Consulta de caminhões, produtos e pedidos |
| `DRIVER` | Acesso limitado ao próprio usuário autenticado |

### Cadastros operacionais

- Cadastro de usuários
- Cadastro de clientes
- Cadastro de motoristas
- Cadastro de caminhões
- Cadastro de produtos
- Cadastro de pedidos
- Histórico de status dos pedidos

### Regras e validações

- Validação dos dados recebidos pela API
- Atualizações parciais utilizando `PATCH`
- Preservação de campos omitidos nas atualizações
- Rejeição de `null` em campos obrigatórios
- Verificação de registros duplicados
- Controle de integridade por constraints do PostgreSQL
- Respostas de erro padronizadas

Estrutura padrão utilizada nos erros de validação:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Os dados informados são inválidos.",
  "details": [
    {
      "field": "name",
      "message": "Mensagem de validação",
      "type": "value_error"
    }
  ]
}
```

### Planejamento inicial de cargas

O projeto já possui primitivas e regras iniciais relacionadas ao planejamento:

- Cálculo de volume
- Expansão das unidades de um pedido
- Controle de peso com precisão decimal
- Verificação da capacidade do caminhão
- Validação de limites físicos
- Validações geométricas
- Identificação de sobreposição entre volumes
- Estrutura inicial para evolução do mecanismo de posicionamento

### Banco de dados

- Banco PostgreSQL
- Models utilizando SQLAlchemy
- Relacionamentos entre entidades
- Constraints de integridade
- Migrations utilizando Alembic
- Histórico controlado da estrutura do banco

### Qualidade e automação

- Testes unitários
- Testes de integração
- Verificação automática com Pytest
- Análise estática com Ruff
- Verificação de tipagem com MyPy
- Análise de segurança
- Integração com SonarCloud
- Pipeline de integração contínua com GitHub Actions
- Verificações automáticas nos Pull Requests

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

##  ARQUITETURA

O backend utiliza uma organização modular para evitar a concentração de regras de negócio diretamente nas rotas da API.

```text
Cliente
   │
   ▼
FastAPI
   │
   ▼
Rotas e dependências
   │
   ▼
Schemas e validações
   │
   ▼
Services e regras de negócio
   │
   ▼
Models e repositórios
   │
   ▼
SQLAlchemy
   │
   ▼
PostgreSQL
```

Cada módulo possui responsabilidades próprias, como:

```text
modules/
├── auth/
├── users/
├── customers/
├── drivers/
├── trucks/
├── products/
├── orders/
└── load_planning/
```

Essa separação facilita:

- Manutenção
- Testes
- Revisão de código
- Evolução dos módulos
- Reutilização de regras
- Integração futura com frontend e serviços externos

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## ⚙️ TECNOLOGIAS E FERRAMENTAS

### Backend

![Python](https://img.shields.io/badge/PYTHON-000000?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-000000?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLALCHEMY-000000?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/PYDANTIC-000000?style=for-the-badge&logo=pydantic&logoColor=white)
![Alembic](https://img.shields.io/badge/ALEMBIC-000000?style=for-the-badge&logoColor=white)

### Banco de dados

![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-000000?style=for-the-badge&logo=postgresql&logoColor=white)

### Testes

![Pytest](https://img.shields.io/badge/PYTEST-000000?style=for-the-badge&logo=pytest&logoColor=white)

### Qualidade

![Ruff](https://img.shields.io/badge/RUFF-000000?style=for-the-badge&logo=ruff&logoColor=white)
![MyPy](https://img.shields.io/badge/MYPY-000000?style=for-the-badge&logo=python&logoColor=white)
![SonarCloud](https://img.shields.io/badge/SONARCLOUD-000000?style=for-the-badge&logo=sonarcloud&logoColor=white)

### DevOps e versionamento

![Docker](https://img.shields.io/badge/DOCKER-000000?style=for-the-badge&logo=docker&logoColor=white)
![Docker Compose](https://img.shields.io/badge/DOCKER_COMPOSE-000000?style=for-the-badge&logo=docker&logoColor=white)
![Git](https://img.shields.io/badge/GIT-000000?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GITHUB-000000?style=for-the-badge&logo=github&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GITHUB_ACTIONS-000000?style=for-the-badge&logo=githubactions&logoColor=white)

### Documentação

![Markdown](https://img.shields.io/badge/MARKDOWN-000000?style=for-the-badge&logo=markdown&logoColor=white)

### Tecnologias previstas

As tecnologias abaixo fazem parte do roadmap e ainda não representam funcionalidades concluídas:

![OpenAI](https://img.shields.io/badge/OPENAI_API-000000?style=for-the-badge&logo=openai&logoColor=white)
![OpenCV](https://img.shields.io/badge/OPENCV-000000?style=for-the-badge&logo=opencv&logoColor=white)
![Three.js](https://img.shields.io/badge/THREE.JS-000000?style=for-the-badge&logo=threedotjs&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WHATSAPP_BUSINESS_API-000000?style=for-the-badge&logo=whatsapp&logoColor=white)

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## FUNCIONALIDADES PREVISTAS

### Planejamento e otimização

- Mecanismo completo de distribuição inteligente de cargas
- Seleção automática do caminhão adequado
- Posicionamento tridimensional dos volumes
- Controle de estabilidade da carga
- Restrições de empilhamento
- Priorização de pedidos
- Aproveitamento do espaço interno do veículo
- Comparação entre diferentes planos de carregamento

### Visualização

- Visualização 3D da carga
- Representação dos produtos dentro do caminhão
- Identificação visual de espaços livres
- Exibição de posições, rotações e dimensões

### Monitoramento

- Monitoramento das operações por câmera
- Processamento de imagens com OpenCV
- Registro de eventos do carregamento
- Comparação entre o plano e a execução real

### Integrações

- Integração com WhatsApp Business API
- Notificações para motoristas
- Avisos sobre liberação de cargas
- Comunicação sobre alterações de pedidos
- Integração com modelos de Inteligência Artificial

### Gestão

- Dashboard logístico
- Rastreamento das entregas
- Relatórios gerenciais
- Indicadores de aproveitamento
- Histórico de planos executados
- Métricas de peso, volume e ocupação

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 🖥️ INSTALAÇÃO

### Pré-requisitos

Antes de iniciar, verifique se possui:

- Python 3.12 ou superior
- PostgreSQL
- Git
- Docker e Docker Compose, caso utilize containers

### Clonar o projeto

```bash
git clone https://github.com/RennaN-C/loadx-smart-logistics.git
cd loadx-smart-logistics
```

### Criar o ambiente virtual

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Instalar as dependências

```bash
pip install -r backend/requirements.txt
```

<div align="center">

──────────── ◇ ────────────

</div>

## 🔐 CONFIGURAÇÃO DO AMBIENTE

Crie o arquivo `.env` com base no `.env.example`.

Configure os dados de conexão com o PostgreSQL e as demais variáveis exigidas pela aplicação.

Exemplo:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/loadx
SECRET_KEY=chave-segura
ENVIRONMENT=local
```

Nunca publique no repositório:

- Senhas
- Tokens
- Chaves de API
- Credenciais do banco
- Arquivos `.env`
- Dados pessoais reais

<div align="center">

──────────── ◇ ────────────

</div>

## 🗄️ BANCO DE DADOS

Acesse o diretório do backend:

```bash
cd backend
```

Aplique as migrations:

```bash
alembic upgrade head
```

Consultar a migration atual:

```bash
alembic current
```

Visualizar o histórico:

```bash
alembic history
```

Desfazer a última migration:

```bash
alembic downgrade -1
```

<div align="center">

──────────── ◇ ────────────

</div>

## 👤 CRIAÇÃO DO PRIMEIRO ADMINISTRADOR

O cadastro público de usuários administrativos não fica disponível pela API.

Para criar o primeiro administrador no ambiente local:

```bash
cd backend
python -m app.modules.auth.bootstrap
```

Depois da criação do primeiro administrador, os demais usuários devem ser gerenciados pelos endpoints protegidos da aplicação.

<div align="center">

──────────── ◇ ────────────

</div>

## ▶️ EXECUTAR O BACKEND

Dentro do diretório `backend`, execute:

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em:

```text
http://localhost:8000
```

No ambiente local, a documentação interativa poderá ser acessada em:

```text
Swagger: http://localhost:8000/docs
ReDoc:   http://localhost:8000/redoc
```

A documentação da API deve permanecer desativada em ambientes que não sejam locais.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 🧪 TESTES E QUALIDADE

### Executar todos os testes

```bash
cd backend
pytest
```

### Executar com mais detalhes

```bash
pytest -v
```

### Executar um arquivo específico

```bash
pytest tests/caminho_do_teste.py
```

### Ruff

```bash
ruff check .
```

### MyPy

```bash
mypy app
```

As verificações automatizadas também são executadas durante os Pull Requests por meio do GitHub Actions e do SonarCloud.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📂 ESTRUTURA DO PROJETO

```text
loadx-smart-logistics/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── database/
│   │   └── modules/
│   │       ├── auth/
│   │       ├── users/
│   │       ├── customers/
│   │       ├── drivers/
│   │       ├── trucks/
│   │       ├── products/
│   │       ├── orders/
│   │       └── load_planning/
│   │
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docs/
│
├── .github/
│   └── workflows/
│
├── .env.example
├── compose.yaml
└── README.md
```

A estrutura poderá evoluir conforme novos módulos forem implementados.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📚 DOCUMENTAÇÃO

A documentação técnica está centralizada no diretório:

```text
docs/
```

Os documentos registram:

- Arquitetura
- Contratos da API
- Regras de negócio
- Decisões técnicas
- Ocorrências identificadas
- Propostas de correção
- Convenções do projeto
- Fluxos dos módulos
- Planejamento das funcionalidades

Alterações que modificam contratos, regras ou comportamentos importantes também devem atualizar a documentação relacionada.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📈 STATUS DO PROJETO

O projeto encontra-se em desenvolvimento ativo.

### Concluído ou em estágio avançado

- Estrutura inicial do backend
- Banco de dados
- Migrations
- Autenticação
- Autorização por perfil
- Cadastros principais
- Histórico de status
- Padronização dos erros da API
- Atualizações parciais
- Testes automatizados
- Integração contínua
- Análise de qualidade
- Primitivas iniciais do planejamento de cargas
- Documentação técnica inicial

### Em desenvolvimento

- Evolução do planejamento de cargas
- Regras de posicionamento
- Validação de capacidade e estabilidade
- Contratos entre planejamento e API
- Ampliação dos testes
- Consolidação da documentação

### Próximas etapas

- Frontend
- Visualização 3D
- Algoritmos completos de otimização
- Dashboard logístico
- Monitoramento
- Integrações externas
- Inteligência Artificial
- Relatórios gerenciais

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 🤝 CONTRIBUIÇÃO

O projeto utiliza um fluxo baseado em Issues, branches e Pull Requests.

### Estrutura de branches

```text
main
  ▲
  │
desenvolvimento
  ▲
  │
feature/<issue>-<descricao>
```

### Fluxo adotado

1. Criar ou selecionar uma Issue
2. Criar uma branch a partir de `desenvolvimento`
3. Implementar a funcionalidade
4. Adicionar ou atualizar os testes
5. Atualizar a documentação afetada
6. Abrir um Pull Request para `desenvolvimento`
7. Aguardar as verificações automáticas
8. Realizar a revisão do código
9. Corrigir os apontamentos encontrados
10. Integrar após aprovação
11. Integrar módulos estáveis em `main`

### Regras para Pull Requests

- Manter o PR relacionado a uma Issue
- Evitar alterações fora do escopo
- Não misturar funcionalidades diferentes
- Incluir testes quando necessário
- Atualizar a documentação relacionada
- Confirmar que os testes continuam passando
- Resolver conflitos antes da integração
- Aguardar a análise do GitHub Actions e SonarCloud
- Solicitar revisão antes do merge

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 🔒 SEGURANÇA

Não devem ser incluídos no repositório:

- Senhas
- Tokens de autenticação
- Chaves de API
- Credenciais do PostgreSQL
- Dados pessoais reais
- Arquivos de ambiente
- Informações internas de infraestrutura

Falhas de segurança não devem ser publicadas com detalhes sensíveis em Issues abertas.

O projeto utiliza validação de entrada, autenticação, autorização por perfil e tratamento controlado de erros para reduzir a exposição de informações internas.

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

</div>

## 📄 LICENÇA

Projeto desenvolvido exclusivamente para fins acadêmicos.

O código não deve ser utilizado em ambiente de produção sem:

- Revisão técnica
- Validação de segurança
- Testes adicionais
- Configuração adequada da infraestrutura
- Autorização dos responsáveis pelo projeto

<div align="center">

━━━━━━━━━━━━━━━━━━━━ ◈ ━━━━━━━━━━━━━━━━━━━━

##  LOAD X

### Tecnologia aplicada à organização, inteligência e evolução das operações logísticas.

</div>
