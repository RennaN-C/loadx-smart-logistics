# ADR-019: inicialização segura e migrations no Compose

Status: aceita

## Contexto

A configuração do backend possuía valores locais como fallback mesmo quando o
ambiente padrão era produção. O Compose publicava PostgreSQL, API e frontend em
todas as interfaces, executava os processos de aplicação com privilégios do
container e dependia de uma aplicação manual das migrations antes de `/ready`
ficar saudável.

Uma auditoria também encontrou dependências vulneráveis no backend e no
frontend. A inicialização precisava falhar de forma segura, e um banco vazio
precisava chegar ao schema oficial sem atribuir escrita ao endpoint de
readiness.

## Decisão

- Produção exige `SECRET_KEY` exclusiva com no mínimo 32 caracteres e
  `DATABASE_URL` diferente do fallback local.
- Produção rejeita origem CORS `*`; JWT aceita somente `HS256` e expiração entre
  1 e 1440 minutos.
- O Compose publica PostgreSQL, backend e frontend apenas em `127.0.0.1` por
  padrão, com portas configuráveis por ambiente.
- Um serviço one-shot `migrate` espera o PostgreSQL saudável e executa `alembic
  upgrade head`. O backend só inicia após sua conclusão com código zero.
- `/ready` permanece estritamente somente leitura e não aplica migrations.
- Backend, migration e frontend executam como usuários sem privilégio, sem
  capabilities Linux e com `no-new-privileges`.
- O PostgreSQL 16 usa autenticação host SCRAM em novos volumes.
- Dependências com advisories conhecidos são substituídas ou atualizadas e os
  scanners de dependência fazem parte da validação desta mudança.

## Consequências

- Configuração de produção incompleta ou insegura interrompe a inicialização em
  vez de colocar uma instância vulnerável em serviço.
- Um banco novo recebe o head Alembic antes de o backend aceitar tráfego.
- Falha de migration impede a API de iniciar e fica visível no container
  `migrate`, sem expor detalhes pelo endpoint público.
- O volume PostgreSQL existente é preservado; `docker compose down -v` continua
  sendo a operação explícita que remove dados locais.
- O Compose permanece um ambiente local de desenvolvimento. Credenciais, TLS,
  rede privada, backup e segregação de papéis do banco em produção continuam
  responsabilidades da infraestrutura de implantação.
