# Issue #336 — Assistente LoadX consultivo

Base: desenvolvimento `3a1e952`. Branch: feat/assistente-loadx-groq-contextual.
Não houve merge, deploy, alteração de tag, conta externa ou segredo real.

## Evidências locais

- Adapter/fábrica/ferramentas: testes unitários com HTTP simulado, êxito,
  timeout, 429/503, saída inválida, falta de chave, RBAC, ferramentas proibidas,
  histórico não confiável, redação e rejeição de alegações de escrita/ganho.
- PostgreSQL 16 isolado: expedição por início real, distinção de pernas e pedido
  totalmente entregue, multi-caminhão sem duplicação, cliente normalizado,
  canceladas com links reais, CSRF, 401/403/404 e concorrência/limite de consulta.
- Frontend completo local: 137 arquivos / 1.154 testes aprovados na primeira
  estabilização; casos adicionais e refino foram revalidados de forma focada.
  Última bateria Assistente + Planejamento: 59 testes aprovados.
- TypeScript, ESLint, build e orçamento de bundle aprovados; Ruff check/format.
- Backend completo local: 3.034 aprovados, uma expectativa antiga de IA real
  no mock identificada. Agora mock retorna FALLBACK, sem enfraquecer 401/403;
  regressão revalidada. A suíte completa final é conferida na CI do HEAD da PR.
- Head Alembic único 20261023_0035, sem migration nova.
- Compose local/produção + override Groq validados com valores fictícios;
  frontend não recebe .env backend e chave Groq usa secret no override.

## Chromium real

`browser-results.json`: oito cenários, 375/768/1280/1920 px e claro/escuro.
FastAPI + PostgreSQL 16 separados dos testes destrutivos. Login normal de conta
CHECKER sintética; sem alterar MFA. Fonte FALLBACK por ausência de configuração,
sem interceptação HTTP. Escape e limites do painel verificados. As capturas
foram inspecionadas; corrigido recorte causado pelo containing block do cabeçalho
com portal, e composer fixo enquanto a conversa rola. Não equivalem a E2E Groq real.

## Limites e decisões

- Nenhuma chave real foi fornecida/utilizada e nenhum envio externo foi realizado.
  Aceite ao vivo exige AI_PROVIDER=groq, chave e modelo válidos no backend.
- Financeiro/ROI/melhoria percentual sem baseline: insufficient_data, sem estimar.
- Período máximo 93 dias; disponibilidade é snapshot paginado atual.
- Rate limit por usuário/processo; advisory lock impede simultaneidade entre
  workers. Teto global por minuto/retentor de auditoria depende de contrato próprio.
- Redação por padrões não é classificador universal de PII. A UI orienta não
  inserir dados pessoais ou segredos; contexto estruturado minimiza dados.
- ADR-048 segue em revisão; sem comandos de escrita ou arquitetura multiempresa.

Seleção ambígua adicional: teste PostgreSQL de dois clientes homônimos confirmou
opções autorizadas, seleção revalidada e ausência de UUIDs/metadados de filtro no
payload do provider; frontend testa seleção sem consulta automática e filtro visível.

## Revalidação dos apontamentos da PR

- TLS explicitamente exige CERT_REQUIRED e hostname; teste captura o contexto
  HTTPS real criado pelo adapter, além de validar endpoint e payload.
- Redação de tokens contendo @ sem expressão de backtracking superlinear.
- Permissões são revalidadas entre chamadas; promoção não amplia ferramentas
  anunciadas e revogação impede consultas pendentes.
- Unitários Groq/orquestração/saúde: 59 aprovados. PostgreSQL 16
  Assistente/saúde/OpenAPI: 37 aprovados. Frontend focado: 16 aprovados.
- Resultados completos e Quality Gate finais são registrados no corpo da PR.

- Placas retornadas pela disponibilidade permanecem nos fatos autorizados da UI;
  teste confirma que não seguem no resultado estruturado enviado à Groq.
- Período com fim explícito e início omitido usa os 30 dias anteriores ao fim
  solicitado, validado em regressão; não usa a data atual como base incoerente.

## Ajustes após revisão — indicadores e tentativa malsucedida

- Texto livre da Groq não cruza mais a fronteira da resposta pública. Catálogo
  fechado de orientações e fontes reais substituem reconhecimento heurístico de
  números. Regressões: 500/quinhentos pedidos, porcentagem inventada, campos extras,
  histórico forjado, consulta real com valor distinto e seleção sem consulta.
- Otimização que falha por capacidade entrega comprovante assinado por 15 minutos,
  do próprio usuário, sem IDs de volumes/caminhões, e o chat verifica a permissão
  atual. Testes rejeitam adulteração, expiração, outro usuário, Unicode malformado
  e acesso CHECKER. O comprovante não é enviado ao provider nem persistido.
- Bateria focada: 60 testes backend aprovados com PostgreSQL 16, incluindo a falha
  real de empacotamento sem persistência parcial, e 29 testes frontend aprovados.
  Ruff check/format (579 arquivos), ESLint, TypeScript e build aprovados.
- Chromium adicional (`review-browser-results.json`): sessão gerencial sintética
  criada por fixture, não teste de login/MFA; navegador → otimização HTTP 422 real
  → ação contextual → chat HTTP 200 real com FALLBACK sem chave Groq. Sem interceptar
  requisições. Dois volumes com COLLISION conferidos no diagnóstico; 8 combinações
  de largura/tema, Escape e rolagem até os indicadores. Capturas desktop/mobile
  `review-diagnostic-*` revisadas. Não é validação externa do provider.
- Contratos de recuperação/idempotência, rollback e limite físico permanecem;
  não houve migration, merge ou deploy. A CI completa do novo HEAD consta na PR.
