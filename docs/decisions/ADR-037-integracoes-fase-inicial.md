# ADR-037 — Integrações por fase

Status: aceita em 10/10/2026.

O LoadX está em desenvolvimento inicial. WhatsApp permanece simulado; integração externa será avaliada na pré-produção (Issue #193).

OC83 desenvolve o recebimento HTTP autenticado, com validação e testes reais, independentemente da Meta. OC84 processa notificações do domínio; somente a saída WhatsApp é simulada. A IA poderá utilizar um serviço real aprovado, com credenciais de ambiente, limites e fallback seguro. Não confundir notificações internas com envio externo.

OC82 (#125) entrega a base mock. A conclusão dessa etapa libera OC83, OC84 e OC108. OC103, OC109 e OC94 continuam dependentes da OC84. Não alterar infraestrutura de produção por esta decisão.
