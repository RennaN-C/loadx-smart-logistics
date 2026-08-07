# ADR-018: readiness com PostgreSQL e Alembic

Status: aceita

## Contexto

`/health` comprova apenas que o processo HTTP está em execução. Esse sinal não
impede que uma instância receba tráfego quando o PostgreSQL está inacessível ou
quando o schema persistido não corresponde às migrations entregues com o
backend.

A D11 precisava separar liveness de readiness sem transformar o endpoint
operacional em uma fonte de detalhes internos.

## Decisão

- `GET /health` permanece como liveness e não consulta banco ou migrations.
- `GET /ready` fica fora de `/api/v1`, é público para uso por Compose, CI e
  monitoramento e não aceita parâmetros.
- Readiness retorna `200` somente quando uma consulta somente leitura ao
  PostgreSQL funciona e o conjunto de revisões em `alembic_version` é exatamente
  igual ao conjunto de heads entregue com a aplicação.
- A verificação executa `SELECT 1`, não altera dados e nunca aplica migrations.
- O orçamento total da verificação é de 2 segundos. A conexão e cada consulta
  recebem apenas o tempo ainda disponível dentro desse orçamento.
- Sucesso retorna `{"status":"ready","service":"loadx-api"}`.
- Banco indisponível, timeout, tabela de versão ausente ou divergência de revisão
  retornam `503` com `SERVICE_NOT_READY`, mensagem genérica e `details` vazio no
  envelope de erro oficial.
- A resposta não informa componente com falha, host, porta, URL, credencial,
  revisão esperada ou encontrada, exceção ou stack trace.
- Logs internos registram somente uma categoria estável da falha. URL de banco,
  credenciais e mensagem bruta do driver não são registradas.
- Falhas inesperadas fora da verificação continuam usando o handler genérico
  `500 INTERNAL_SERVER_ERROR`.

## Consequências

- `/health` pode continuar saudável durante indisponibilidade do banco; isso é
  intencional porque mede apenas liveness.
- Instâncias com banco inacessível ou schema divergente não ficam prontas para
  tráfego operacional.
- Deploys devem aplicar migrations antes de esperar sucesso em `/ready`.
- Compose e CI podem consumir `/ready` sem possuir token de usuário.
- A fronteira pública passa a incluir dois endpoints operacionais, `/health` e
  `/ready`, além do login.

