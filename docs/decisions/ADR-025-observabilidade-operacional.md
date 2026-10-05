# ADR-025 — Observabilidade operacional sem fornecedor obrigatório

Status: proposta, implementada para revisão na OC77 (#59).

## Contexto

`CONFIRMADO`: health/ready e eventos de segurança já existem. Logs de falhas de
notificação incluíam tracebacks, e logs HTTP podiam conter URI/query string ou
dados pessoais. Produção utiliza Uvicorn com workers e Caddy (ADR-021).

## Decisão proposta

`RECOMENDAÇÃO`: usar JSON em stdout por processo, com eventos e campos técnicos
permitidos explicitamente, sem SDK ou fornecedor. Um UUID gerado pelo servidor
correlaciona eventos e `X-Request-ID`; IDs enviados pelo cliente não são usados.
Requisições registram método, template da rota, status e duração. Caminhos não
reconhecidos usam `__unmatched__`. Não registrar valores de parâmetros,
query strings, corpo, cookies, headers, IP, telefone, senha, URL de banco ou
mensagens/tracebacks de exceções.

`CONFIRMADO`: a implementação inclui falha inesperada, indisponibilidade de
readiness, falha de notificação e ciclo de vida. Logs HTTP nativos do Uvicorn
ficam desativados; seu logger de erro remove traceback/payload de exceções.
Caddy remove URI, headers e endereços dos logs de acesso. A API continua com
respostas genéricas de erro; `/ready` não aplica migrations.

## Consequências

`CONFIRMADO`: métricas de tráfego, latência e taxa de 5xx podem ser derivadas dos
eventos por qualquer coletor, somando todos os workers. Não há contador global
em memória nem endpoint público de métricas. `alert=true` marca candidatos a
alerta; emissão de eventos não equivale a entrega de notificação externa.

`PENDENTE DE DEFINIÇÃO`: aprovação desta ADR, coletor, destino, retenção,
limiares, SLA, destinatários e eventual exporter de métricas. Não contratar
serviço ou habilitar envio externo com esta alteração.

`RISCO IDENTIFICADO`: desligar logs HTTP ou elevar o nível remove dados usados
para agregação. Destino e retenção precisam ser definidos antes de afirmar que há
observabilidade centralizada em produção. Tracebacks completos ficam omitidos
por segurança; diagnóstico começa no tipo de exceção e template de rota.
