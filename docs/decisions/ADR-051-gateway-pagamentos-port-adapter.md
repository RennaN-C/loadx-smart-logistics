# ADR-051 — Gateway de pagamentos por port/adapters

- **Status:** PROPOSTA — provedor inicial ainda não selecionado.
- **Escopo:** billing e assinaturas SaaS do LoadX.
- **Relacionada:** ADR-050 — Control plane comercial e ownership de licenças SaaS.
- **Não altera:** código, secrets, credenciais ou pagamentos atuais.

## Contexto

O LoadX precisa gerar cobranças recorrentes, conciliar pagamentos, renovar assinaturas e ativar entitlements somente após confirmação financeira. Foram avaliados preliminarmente Asaas e Mercado Pago com base nas documentações oficiais consultadas em 14/11/2026.

## Decisão proposta

### 1. Abstração obrigatória

O domínio depende de uma porta BillingGateway; adapters implementam cada provedor.

Operações mínimas:
- criar/localizar cliente;
- criar checkout de primeira contratação;
- criar ou administrar recorrência;
- consultar cobrança, fatura e assinatura;
- cancelar renovação/assinatura;
- validar assinatura/token de webhook;
- normalizar eventos externos.

Nenhum service de assinatura importa SDK ou payload específico do provedor.

### 2. Um provedor na primeira entrega

O primeiro lançamento integra somente um provedor. A arquitetura suporta mais de um adapter, mas a implementação simultânea dos dois não faz parte da primeira entrega.

A troca do provedor padrão não migra automaticamente assinaturas existentes. Tokens de cartão e credenciais não são transferidos entre provedores; quando necessário, o cliente autoriza novo checkout.

### 3. Avaliação preliminar

**Asaas**
- API REST com cobranças e assinaturas.
- Assinaturas documentadas com boleto, Pix e cartão.
- Checkout hospedado com Pix e cartão, inclusive recorrência.
- Webhooks com entrega at-least-once e necessidade de idempotência por ID do evento.
- Pix Automático documentado, após autorização do pagador e sujeito a requisitos de elegibilidade da conta recebedora.
- Candidato preliminar recomendado para a primeira homologação.

Documentação:
- https://docs.asaas.com/docs/visao-geral
- https://docs.asaas.com/docs/assinaturas
- https://docs.asaas.com/docs/checkout-asaas
- https://docs.asaas.com/docs/pix-automatico
- https://docs.asaas.com/docs/webhooks-2
- https://www.asaas.com/precos-e-taxas

**Mercado Pago**
- API de assinaturas com e sem plano associado.
- Faturas, pagamentos, gestão de assinatura e tentativas automáticas.
- Documentação de assinaturas lista meios online e offline, incluindo Pix e boleto.
- Webhooks autenticados por assinatura HMAC no header x-signature.
- Produto avançado de pagamentos automáticos sem CVV utiliza cartão armazenado e exige habilitação comercial; não deve ser confundido com geração de faturas recorrentes.
- Alternativa válida, sujeita à confirmação de custos e elegibilidade comercial.

Documentação:
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/additional-content/your-integrations/notifications/webhooks
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/overview
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/prerequisites

### 4. Gate comercial antes da seleção

Registrar uma comparação formal com:
- tarifas contratadas por Pix, boleto, cartão e recorrência;
- custo de estorno, chargeback e antecipação;
- prazo de liquidação e disponibilidade de saldo;
- retentativas e regras de cobrança recusada;
- elegibilidade e ativação de Pix Automático;
- limites de API, Sandbox, suporte e homologação;
- experiência de checkout e atualização do meio de pagamento.

Tarifas promocionais públicas não bastam para escolher. A seleção final exige condição comercial aplicável à conta do LoadX.

### 5. Segurança e consistência

- Usar checkout hospedado ou tokenização para que o LoadX não armazene PAN/CVV.
- Guardar credenciais somente em secret manager/ambiente de backend.
- Usar idempotency key em toda criação de cobrança/checkout.
- O redirect do navegador nunca confirma pagamento.
- Webhook é endpoint sem sessão de usuário, mas exige autenticação criptográfica/token do provedor.
- Persistir metadados mínimos do evento em inbox antes de processamento demorado.
- Deduplicar por provedor e ID de evento.
- Consultar o recurso financeiro no provedor antes de confirmar pagamento.
- Atualizar pagamento, fatura, assinatura e entitlement de forma transacional.
- Suportar reenvio, evento fora de ordem e reconciliação periódica.
- Não armazenar payload bruto com dados sensíveis sem justificativa e política de retenção.

### 6. Regra de ativação

Somente pagamento consultado e confirmado no provedor pode:
- marcar a fatura como paga;
- estender paid_through_at;
- ativar ou renovar a assinatura;
- materializar entitlements.

Evento inválido, pagamento pendente, redirect de sucesso ou criação de assinatura não liberam acesso.

## Consequências

- A regra comercial permanece independente do gateway.
- É possível homologar outro provedor sem reescrever billing.
- O primeiro lançamento tem menor superfície operacional por integrar um único provedor.
- A seleção depende de proposta comercial, conta elegível e Sandbox; não está concluída nesta ADR.
