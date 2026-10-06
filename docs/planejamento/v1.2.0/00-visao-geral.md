# Planejamento da v1.2.0

## Objetivo

`CONFIRMADO`: a v1.2.0 é o ciclo pós-v1.1.0 voltado a fechar lacunas de
administração, transformar comunicação/evidências simuladas em integrações reais,
permitir operação com múltiplos caminhões e completar fluxos básicos esperados
de um produto operacional.

`CONFIRMADO`: a versão usa **OC79–OC96**, formalizadas nas Issues **#122–#133**
e **#136–#141**. A descrição detalhada, critérios de aceite e branches sugeridas
permanecem nas Issues; este arquivo consolida escopo, responsáveis, dependências e fluxo.

`CONFIRMADO`: multiempresa/multitenancy **não faz parte da v1.2.0**. A OC91
cadastra os dados gerais da empresa atual. A plataforma multiempresa está somente
no roadmap da v1.3.0 e ainda não possui OCs ou Issues funcionais.

## Divisão oficial

| OC | Issue | Responsável | Área | Dependência principal |
|---|---:|---|---|---|
| OC79 | #122 | Rennan | Segurança / integrações | Nenhuma OC anterior da v1.2.0 |
| OC80 | #123 | Rennan | Entregas / evidências | Alinhar idempotência com OC79 |
| OC81 | #124 | Marlon | Frontend / comprovante | OC80 |
| OC82 | #125 | Marcelo | Integração / WhatsApp | OC79 |
| OC83 | #126 | Marcelo | Integração / webhook e mídia | OC79, OC80 e OC82 |
| OC84 | #127 | Marcelo | Integração / notificações | OC79 e OC82 |
| OC85 | #128 | Marlon | Frontend / configurações | Nenhuma OC anterior da v1.2.0 |
| OC86 | #129 | Marlon | Frontend / usuários | OC85 |
| OC87 | #130 | Rennan | Domínio / multi-caminhão | Nenhuma OC anterior; exige ADR |
| OC88 | #131 | João | Algoritmo / multi-caminhão | OC87 |
| OC89 | #132 | Marlon | Frontend / multi-caminhão | OC87 e OC88 |
| OC90 | #133 | Marcelo | Operação / auditoria | OC87 e OC88 |
| OC91 | #136 | Rennan | Configurações / empresa atual | OC85 |
| OC92 | #137 | Rennan | Conta / segurança | OC85 |
| OC93 | #138 | Marlon | Frontend / central operacional | OC90 e OC94 |
| OC94 | #139 | Marcelo | Operação / exceções | OC87 e OC84 |
| OC95 | #140 | João | Consultas / filtros | Nenhuma OC bloqueadora |
| OC96 | #141 | Marcelo | Relatórios / exportações | OC90 e OC94 |

## Frentes da versão

### Administração e conta

- OC85 cria a área de Configurações restrita ao ADMIN.
- OC86 expõe no frontend a gestão de usuários já protegida pelo backend.
- OC91 adiciona os dados gerais da empresa atual sem implementar multiempresa.
- OC92 cria Meu perfil, alteração de senha e gestão de sessões do próprio usuário.

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

### Acabamento operacional e gerencial

- OC93 cria a central de carregamentos, viagens e entregas.
- OC94 completa o caminho de exceção com falha, ausência, reentrega e cancelamento.
- OC95 leva busca e filtros para o servidor antes da paginação.
- OC96 cria relatórios gerenciais e exportações coerentes com os dados do backend.

## Ordem recomendada de execução

`RECOMENDAÇÃO`:

1. iniciar em paralelo OC79, OC80, OC85, OC87 e OC95;
2. após OC85, liberar OC86, OC91 e OC92;
3. após OC79, liberar OC82; depois liberar OC83/OC84 conforme suas dependências;
4. após OC87, executar OC88 e depois integrar OC89/OC90;
5. após OC87 e OC84, executar OC94;
6. após OC90 e OC94, executar OC93 e OC96;
7. integrar OC81 após OC80 e os contratos externos necessários;
8. validar a suíte completa em `desenvolvimento`, preparar `versao/v1.2.0` e
   promover para `main` somente após todos os gates.

## Decisões obrigatórias

`DECISÃO NECESSÁRIA`: antes de armazenamento real de evidências, definir
retenção, armazenamento, acesso, proteção e remoção.

`DECISÃO NECESSÁRIA`: antes de alteração estrutural do multi-caminhão, a OC87
deve registrar ADR cobrindo cardinalidades, rastreabilidade, aprovação parcial,
divisão/recomposição, cancelamento/recálculo e compatibilidade.

`DECISÃO NECESSÁRIA`: a OC94 deve registrar estados e transições permitidos para
ausência, recusa, falha, reentrega e cancelamento.

## Regras permanentes

- backend continua sendo a autoridade de autenticação e autorização;
- integrações externas permanecem atrás de adaptadores;
- mensagens externas nunca escrevem diretamente no banco;
- o frontend não calcula distribuição multi-caminhão;
- busca/filtro de grandes coleções deve ocorrer no servidor antes da paginação;
- indicadores e relatórios gerenciais não inventam métricas no frontend;
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

- [x] milestone `v1.2.0` criado;
- [x] Issues #122–#133 e #136–#141 vinculadas ao milestone;
- [ ] Issues #122–#133 e #136–#141 adicionadas ao Project `LoadX — Desenvolvimento`;
- [x] dependências definidas no planejamento e automação;
- [ ] status iniciais definidos no Project;
- [x] validação automática de PR apontando para v1.2.0;
- [x] bot/automação apontando para v1.2.0.
