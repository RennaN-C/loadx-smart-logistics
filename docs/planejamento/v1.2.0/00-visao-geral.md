# Planejamento da v1.2.0

## Objetivo

`CONFIRMADO`: a v1.2.0 é o ciclo pós-v1.1.0 voltado a fechar lacunas de
administração, transformar comunicação/evidências simuladas em integrações reais
e permitir planejamento e operação com múltiplos caminhões.

`CONFIRMADO`: a versão usa **OC79–OC90**, formalizadas nas Issues **#122–#133**.
A descrição detalhada, critérios de aceite e branches sugeridas permanecem nas
Issues; este arquivo consolida escopo, responsáveis, dependências e fluxo.

## Divisão oficial

| OC | Issue | Responsável | Área | Dependência principal |
|---|---:|---|---|---|
| OC79 | #122 | Rennan | Segurança / integrações | Nenhuma OC anterior da v1.2.0 |
| OC80 | #123 | Rennan | Entregas / evidências | Alinhar idempotência com OC79 |
| OC81 | #124 | Marlon | Frontend / comprovante | OC80; comunicação integra com OC82/OC84 quando disponível |
| OC82 | #125 | Marcelo | Integração / WhatsApp | OC79 |
| OC83 | #126 | Marcelo | Integração / webhook e mídia | OC79 e OC80; alinhar provider com OC82 |
| OC84 | #127 | Marcelo | Integração / notificações | OC79 e OC82 |
| OC85 | #128 | Marlon | Frontend / configurações | Nenhuma OC anterior da v1.2.0 |
| OC86 | #129 | Marlon | Frontend / usuários | OC85 |
| OC87 | #130 | Rennan | Domínio / multi-caminhão | Nenhuma OC anterior; exige ADR antes de mudança estrutural |
| OC88 | #131 | João | Algoritmo / multi-caminhão | OC87 |
| OC89 | #132 | Marlon | Frontend / multi-caminhão | OC87 e OC88 |
| OC90 | #133 | Marcelo | Operação / auditoria | OC87 e OC88; validar junto de OC89 |

## Frentes da versão

### Administração

- OC85 cria a área de Configurações restrita ao ADMIN.
- OC86 expõe no frontend a gestão de usuários já protegida pelo backend.

### Comunicação e comprovante

- OC79 estabelece autenticação, autorização e idempotência de comandos externos.
- OC80 define evidências e comprovante.
- OC81 entrega a experiência operacional.
- OC82–OC84 implementam WhatsApp real, webhook, mídia e notificações.

### Planejamento multi-caminhão

- OC87 define cardinalidades, estados e rastreabilidade.
- OC88 distribui volumes de forma determinística entre veículos.
- OC89 torna o resultado utilizável e visualizável no frontend.
- OC90 fecha carregamento, viagens, entregas, relatórios, auditoria e E2E.

`CONFIRMADO`: o sistema deve continuar preferindo **um único caminhão** quando
ele comportar integralmente a carga. Múltiplos veículos entram quando necessário
e permitido pelas regras da frota.

## Ordem recomendada de execução

`RECOMENDAÇÃO`:

1. iniciar em paralelo OC79, OC80, OC85 e o desenho/ADR da OC87;
2. após os contratos necessários, executar OC82, OC86 e OC88;
3. integrar OC81 após OC80 e os contratos de comunicação disponíveis;
4. executar OC83/OC84 sobre a base de OC79/OC82 e OC80 quando houver mídia;
5. executar OC89 sobre OC87/OC88;
6. concluir OC90 após o fluxo multi-caminhão estar integrado;
7. validar a suíte completa em `desenvolvimento`, preparar `versao/v1.2.0` e
   promover para `main` somente após todos os gates.

## Decisões obrigatórias

`DECISÃO NECESSÁRIA`: antes de armazenamento real de evidências, definir
retenção, armazenamento, acesso, proteção e remoção.

`DECISÃO NECESSÁRIA`: antes de alteração estrutural do multi-caminhão, a OC87
deve registrar ADR cobrindo:

- cardinalidade entre pedido, plano, caminhão, viagem e entrega;
- rastreabilidade por volume;
- aprovação parcial/total;
- divisão e recomposição;
- cancelamento e recálculo;
- migration e compatibilidade dos contratos atuais.

## Regras permanentes

- backend continua sendo a autoridade de autenticação e autorização;
- integrações externas permanecem atrás de adaptadores;
- mensagens externas nunca escrevem diretamente no banco;
- o frontend não calcula distribuição multi-caminhão;
- o algoritmo continua determinístico e não pode aceitar solução fisicamente inválida;
- nenhum volume pode desaparecer ou ser carregado/entregue duas vezes;
- o fluxo de um único caminhão precisa continuar compatível.

## Fluxo Git

`CONFIRMADO`: o fluxo da v1.2.0 é:

```text
branch da ocorrência -> desenvolvimento -> versao/v1.2.0 -> main
```

`CONFIRMADO`: branches, commits e descrições operacionais deste ciclo devem ser
escritos em português, preservando apenas termos técnicos e identificadores que
não possuam tradução adequada.

## Gates antes de iniciar

- [ ] milestone `v1.2.0` criado;
- [ ] Issues #122–#133 vinculadas ao milestone;
- [ ] Issues #122–#133 adicionadas ao Project `LoadX — Desenvolvimento`;
- [ ] dependências registradas;
- [ ] status iniciais definidos;
- [ ] validação automática de PR apontando para v1.2.0;
- [ ] bot/automação do Project apontando para v1.2.0.
