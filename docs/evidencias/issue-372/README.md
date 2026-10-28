# Issue #372 — 3D protagonista no planejamento

Base `73fd043`; PR independente do Loxi. Não houve merge, deploy, dependência,
migration, alteração de backend ou de dados geométricos/limites físicos.

## Comparação real

Capturas `before-*` são da interface congelada em `73fd043`, com a mesma base
PostgreSQL 16 isolada. `after-*` e `expanded-*` são da interface desta branch.
Antes, a aba inicial não montava o 3D. Depois, uma única cena é exibida inicialmente:

| Resultado (1280×900) | Antes | Depois |
|---|---|---|
| Plano individual | Cena atrás da aba | Canvas começa em aproximadamente 590 px |
| Distribuição | Cena após blocos e aba | Canvas começa em aproximadamente 588 px |

Resumo/seleção ficaram compactos; continuidade, dados técnicos e explicação foram
reposicionados, sem remover ações. Cabeçalho e seleção continuam indicando o estado
real. A tabela permanece acessível. Não é comparação com PNGs novos recebidos:
as três novas capturas mencionadas no pedido não estavam anexadas.

## Executado

- 140 testes frontend focados: Modal/ciclo compartilhado, geometria/câmeras,
  viewer, página individual, distribuição e resumo. Expansão mantém o mesmo nó da
  cena e a vista escolhida; Escape restaura foco/scroll. Troca sem key no consumidor
  não mantém geometria anterior enquanto a nova consulta está pendente.
- Seleção de dez veículos tem um seletor compacto e uma cena, sem cálculo novo.
  Transições operacionais, confirmações, retomada e links existentes preservados.
- ESLint: zero erros, dois avisos preexistentes no Assistant da base (tratados na
  PR separada do Loxi). TypeScript e build aprovados. Bundle LoadViewer 230,2 KiB
  gzip, frente a 229,6 KiB da base, dentro do budget de 250 KiB. Sem novos pacotes.
- Chromium real/SwiftShader + API/PostgreSQL isolados, sem interceptação HTTP:
  16 combinações (individual/distribuição × quatro larguras × claro/escuro),
  seleção de caminhão, volume/sequência, F5, expansão sem remount e resize do canvas.
- Cinco perfis: ADMIN/LOGISTICS_MANAGER/CHECKER autorizados para os planos aprovados;
  DRIVER/CUSTOM sem concessões negados. CUSTOM adicional recebeu somente planning.read
  pela API administrativa real no banco QA: viewer permitido, sem aprovação e sem
  novo acesso ao chat. Sessões são fixtures sintéticas, não teste de login/MFA.
- Chromium com WebGL desabilitado: erro amigável e tabela operacional disponíveis.
  Expansão/fechamento também testados em mobile. `browser-results.json` registra
  as condições, resultados e limites; capturas desktop, mobile e modo expandido.

## Limites e continuidade

Não foi medida performance em GPU física nem FPS de produção; SwiftShader é CPU.
Não foi executada suíte backend completa por mudanças apenas frontend. A CI completa
foi disparada normalmente na PR e não será aguardada nesta execução. Segurança e
Sonar ficam para acompanhamento no GitHub. Percentual de cobertura global não foi
recalculado e não se presume importação de cobertura no Sonar.

O inventário mantém Planejamento/Distribuição/3D em EM_CORREÇÃO para aceite visual
contra as referências novas ausentes; os testes funcionais acima estão comprovados.
Não declara as 39 telas globais aprovadas.
