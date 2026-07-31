<div align="center">

# 🚚 LOAD X - Sistema Operacional Logístico Inteligente

### Planejamento e gestão inteligente de cargas utilizando Inteligência Artificial

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Equipe](https://img.shields.io/badge/equipe-4%20desenvolvedores-blue)
![Python](https://img.shields.io/badge/Python-Backend-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Banco%20de%20Dados-336791)

</div>

---

# 👥 Integrantes

- Rennan de Oliveira Cardoso
- Marlon Myszka
- Marcelo Barbusa
- Joao Victor Weber
  

---

# 📌 Resumo da automação proposta

O **LOAD X** é um sistema desenvolvido para automatizar o gerenciamento logístico de empresas de transporte.

A proposta é centralizar o cadastro de clientes, motoristas, caminhões, produtos e pedidos, permitindo que futuramente algoritmos de Inteligência Artificial realizem a distribuição inteligente das cargas, considerando restrições de peso, dimensões e capacidade dos veículos.

Além disso, o sistema prevê recursos para monitoramento das operações, visualização do carregamento, acompanhamento das entregas e apoio à tomada de decisão.

---

# 🎯 Objetivos

- Automatizar processos logísticos.
- Reduzir erros operacionais.
- Otimizar o espaço disponível nos caminhões.
- Melhorar o planejamento das entregas.
- Fornecer informações em tempo real para gestores.

---

# ⚙ Tecnologias e ferramentas utilizadas

## Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## Testes

- Pytest

## Qualidade

- Ruff
- MyPy
- SonarCloud

## DevOps

- Docker
- Docker Compose
- Git
- GitHub
- GitHub Actions

## Documentação

- Markdown

## Tecnologias previstas

- OpenAI API
- OpenCV
- Three.js
- WhatsApp Business API

---

# ✅ Funcionalidades implementadas

Atualmente o backend possui:

- Cadastro de usuários
- Autenticação
- Cadastro de clientes
- Cadastro de motoristas
- Cadastro de caminhões
- Cadastro de produtos
- Cadastro de pedidos
- Histórico de status
- Estrutura inicial do banco de dados
- Migrations utilizando Alembic
- Testes unitários
- Pipeline de integração contínua
- Análise de qualidade com SonarCloud

---

# 🚀 Funcionalidades previstas

- IA para distribuição inteligente de cargas
- Visualização 3D do carregamento
- Monitoramento por câmera
- Integração com WhatsApp
- Dashboard logístico
- Rastreamento das entregas
- Relatórios gerenciais
- Algoritmos de otimização logística

---

# 🖥 Instalação

## Pré-requisitos

- Python 3.12+
- PostgreSQL
- Git
- Docker (opcional)

## Clonar o projeto

```bash
git clone https://github.com/RennaN-C/loadx-smart-logistics.git

cd loadx-smart-logistics
```

## Criar ambiente virtual

Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

## Instalar dependências

```bash
pip install -r backend/requirements.txt
```

## Configurar banco

Criar o arquivo `.env` utilizando o `.env.example` e configurar os dados de conexão com o PostgreSQL.

## Executar as migrations

```bash
cd backend

alembic upgrade head
```

## Executar o backend

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em:

```
http://localhost:8000
```

Documentação Swagger:

```
http://localhost:8000/docs
```

---

# 📂 Estrutura do projeto

```text
backend/
 ├── app/
 ├── migrations/
 ├── tests/
 ├── requirements.txt
 └── Dockerfile

docs/

.github/
```

---

# 📈 Status do projeto

O projeto encontra-se em desenvolvimento.

Atualmente a equipe concluiu a estrutura inicial do backend, banco de dados, autenticação, cadastros principais e testes unitários.

As próximas etapas envolvem a implementação da Inteligência Artificial, frontend, visualização 3D, integração com serviços externos e conclusão da documentação técnica.

---

# 🤝 Contribuição

O projeto utiliza GitHub Flow adaptado para a equipe.

Fluxo de desenvolvimento:

1. Criar uma Issue.
2. Criar uma branch própria.
3. Desenvolver.
4. Abrir Pull Request.
5. Revisão de código.
6. Merge para `desenvolvimento`.
7. A cada módulo importante feito, Merge para `main`.

---

# 📄 Licença

Projeto desenvolvido exclusivamente para fins acadêmicos.

---

<div align="center">

### 🚚 LOAD X

**Tecnologia transformando logística em inteligência operacional.**

</div>
