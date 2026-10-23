# ADR-046: reduzir trabalho físico redundante no planejamento

Status: proposta para revisão — Issue #261, diagnóstico #254, auditoria #256.

## Contexto

`CONFIRMADO`: o profiling sintético de 100 volumes atribuiu aproximadamente 87%
do tempo perfilado à validação de apoio. Cada tentativa rejeitada analisava a
configuração completa duas vezes. A busca multicaminhão repetia o mesmo cálculo
para veículos com capacidade física idêntica, diferenciados apenas pelo UUID.

## Decisão proposta

- Indexar os apoios pelo topo vertical: apenas volumes cujo topo coincide com a
  base examinada podem formar contatos. União de áreas, ancestrais, cobertura de
  100%, fragilidade e empilhamento continuam obedecendo à ADR-010.
- Rejeitar antecipadamente falta de apoio ou uso direto de suporte frágil/não
  empilhável. A função rápida é **somente de rejeição**: resultado vazio nunca
  aprova um candidato. A configuração completa continua sendo analisada antes de
  cada aceitação e novamente na revalidação final da engine.
- A engine mantém um prefixo de posições já fisicamente válido e sem colisões.
  Assim, violações locais identificadas no candidato já são suficientes para
  rejeitá-lo, sem recalcular configurações previamente aprovadas para obter o
  mesmo diagnóstico. Regressões comparam os motivos com a análise completa.
- Compartilhar resultados, somente dentro de uma execução, pela capacidade
  imutável completa e pelo conjunto ordenado de identidades dos volumes.
  Capacidade diferente não compartilha cálculo. Cada parte mantém o UUID do seu
  próprio caminhão e as identidades físicas originais.
- `attempt_count` continua contando execuções efetivas da engine; cache hits não
  incrementam esse contador. Não é contagem de veículos examinados.

## Limites e validação

`CONFIRMADO`: nenhuma regra física, first-fit, ordenação, desempate, estado,
restrição transacional ou limite de 200 volumes/10 caminhões/64 estados muda.
Não há migration ou nova dependência. As propostas continuam sendo revalidadas
pelo service antes de persistir e não se salva uma partição incompleta.

`CONFIRMADO`: o benchmark do motor é separado de HTTP/PostgreSQL e não representa
promessa de latência em Render. Resultados, dados sintéticos, repetições e casos
censurados estão em `docs/evidencias/qa-v12-pentest/performance-254.md`.

`PENDENTE DE DEFINIÇÃO`: orçamento HTTP e idempotência continuam na Issue #254;
esta decisão não transforma timeout em autorização para repetir uma operação e
não implementa processamento assíncrono.
