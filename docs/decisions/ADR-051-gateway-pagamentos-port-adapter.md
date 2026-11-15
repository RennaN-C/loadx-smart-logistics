# ADR-051 — Gateway de pagamentos por port/adapters

- **Status:** PROPOSTA — provedor inicial ainda não selecionado.
- **Escopo:** billing e assinaturas SaaS do LoadX.
- **Relacionada:** ADR-050 — Control plane comercial e ownership de licenças SaaS.
- **Não altera:** código, secrets, credenciais ou pagamentos atuais.

## Contexto

O LoadX precisa gerar cobranças recorrentes, conciliar pagamentos, renovar assinaturas e ativar entitlements somente após confirmação financeira. Foram avaliados preliminarmente Asaas e Mercado Pago com base nas documentações oficiais e páginas públicas de tarifas consultadas em 14/11/2026.

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

### 3. Avaliação atualizada (14/11/2026)

#### Asaas

**Recorrência e meios de pagamento**
- A API oferece cobranças e assinaturas recorrentes.
- Assinaturas podem gerar cobranças por boleto/Pix e cartão de crédito.
- Boleto e Pix em assinatura geram uma cobrança a cada ciclo, mas o pagador precisa efetuar cada pagamento. Um QR Code Pix na fatura não é débito automático.
- Cartão de crédito pode ser cobrado automaticamente nas datas da assinatura.
- Pix Automático é um produto separado: exige autorização prévia do pagador; a jornada inicial combina pagamento e consentimento em QR Code. Só depois do evento de ativação a autorização pode ser usada nos ciclos seguintes.
- No Pix Automático, `paymentCreationMode` pode ser `MANUAL` (a aplicação cria cada cobrança) ou `SUBSCRIPTION` (o Asaas gera as cobranças pela assinatura).

**Elegibilidade do Pix Automático**
A documentação atual lista como critérios: conta PJ aprovada, sem pendências cadastrais, CNPJ ativo há pelo menos seis meses e sem restrições relacionadas ao Pix. A elegibilidade pode mudar e deve ser acompanhada pelo evento `PIX_AUTOMATIC_RECURRING_ELIGIBILITY_UPDATED`. A condição efetiva precisa ser confirmada na conta do LoadX.

**Tarifas públicas e variação por visualização**
- Pix e boleto: a página oficial apresentou valores diferentes entre visualizações consultadas em 14/11/2026. Foram observados pares de R$ 1,59/R$ 0,79 e R$ 2,15/R$ 1,08; o índice da própria página também retornou R$ 1,99/R$ 0,99. Não há base segura para fixar um único valor público como tarifa aplicável à conta LoadX.
- O FAQ do Pix Automático informa que não há custo adicional pelo produto: aplicam-se as taxas padrão de recebimento Pix da conta. Portanto, a tarifa efetiva deve ser capturada no painel Asaas em **Menu do usuário → Taxas**.
- Cartão de crédito: R$ 0,49 + 2,99% à vista; R$ 0,49 + 3,49% de 2 a 6 parcelas; R$ 0,49 + 3,99% de 7 a 12; R$ 0,49 + 4,29% de 13 a 21. A página também exibe percentuais promocionais menores para novos clientes, sujeitos às regras e ao prazo promocional.
- As condições do contrato podem diferir das tarifas padrão; a conta deve ser consultada antes da decisão.
- Antecipação tem custos e análise próprios; não confundir prazo de liquidação padrão com antecipação.

Fontes oficiais:
- https://docs.asaas.com/docs/assinaturas
- https://docs.asaas.com/docs/faq-assinaturas
- https://docs.asaas.com/docs/pix-automatico
- https://docs.asaas.com/docs/faq-2
- https://docs.asaas.com/docs/eventos-para-pix-autom%C3%A1tico
- https://central.ajuda.asaas.com/hc/pt-br/articles/41912520942235-Quais-s%C3%A3o-as-taxas-do-Pix-Autom%C3%A1tico-no-Asaas
- https://www.asaas.com/precos-e-taxas

#### Mercado Pago

**Assinaturas e pagamentos automáticos são produtos diferentes**
- A solução pública de Assinaturas descreve cobranças recorrentes e menciona meios online/offline como Pix e boleto.
- Entretanto, a referência técnica de assinatura com plano associado exemplifica a criação de `preapproval` com `card_token_id`; a tabela geral de meios de pagamento marca boleto como indisponível para Assinaturas. Há uma divergência de escopo/documentação que precisa ser resolvida na conta e no Sandbox antes de prometer Pix ou boleto recorrente pela API.
- Até a homologação, tratar Pix/boleto no fluxo de assinatura como meios que podem exigir ação do pagador em cada ciclo; não classificá-los como débito automático.
- O produto separado **Pagamentos Automáticos (Payments API)** oferece transações iniciadas pelo comerciante (MIT) com cartão armazenado, sem solicitar CVV em cada cobrança. Exige conta de vendedor, contato comercial e habilitação específica da aplicação pelo Mercado Pago. Não é Pix Automático e não substitui autorização de débito Pix.
- A documentação desse produto descreve CIT para o primeiro pagamento/consentimento e MIT para cobranças recorrentes iniciadas pelo comerciante.

**Tarifas públicas de Checkout online**
- Uma visualização da página oficial consultada em 14/11/2026 exibia Pix a 0,99%; cartão a 4,98% na hora, 4,49% em 14 dias ou 3,98% em 30 dias; boleto a R$ 3,49 em até três dias.
- Outras visualizações públicas do Checkout exibiram 4,48% em 14 dias, 2,95% em 30 dias e boleto a R$ 3,99. Isso reforça que a página/condição exibida pode variar; confirmar os valores e prazos no painel da conta.
- São referências públicas de Checkout online, não uma proposta contratada para a API de Assinaturas ou Pagamentos Automáticos. Não transportar automaticamente essas tarifas para produtos avançados.

Fontes oficiais:
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/subscriptions/overview
- https://www.mercadopago.com.br/developers/pt/docs/subscriptions/integration-configuration/subscription-associated-plan
- https://www.mercadopago.com.br/developers/pt/docs/sales-processing/payment-methods
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/overview
- https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/prerequisites
- https://www.mercadopago.com.br/ferramentas-para-vender/check-out

#### Leitura preliminar

Asaas apresenta uma rota documentada para débito recorrente via Pix, condicionada à elegibilidade e à autorização do pagador. Mercado Pago apresenta uma rota avançada de pagamentos MIT com cartão armazenado, sujeita à aprovação comercial e habilitação da aplicação. As assinaturas padrão dos dois provedores não devem ser tratadas como equivalentes a débito automático em todos os meios.

Os preços públicos sugerem que a tarifa fixa do Asaas e a tarifa percentual do Mercado Pago podem inverter a vantagem conforme o ticket; porém, os produtos e prazos de recebimento não são perfeitamente equivalentes. Nenhum cálculo público substitui a proposta e a tabela efetiva da conta do LoadX.

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
