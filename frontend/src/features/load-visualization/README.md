# Feature: load-visualization

Visualização 3D da carga (OC31), interação (OC32) e animação do carregamento (OC33).
Consome `GET /load-plans/{id}/visualization`.

## O que existe hoje

- `components/LoadViewer.tsx` (+ `.css`): busca a visualização, monta a cena, a legenda, o painel de
  detalhe do volume selecionado e os controles de animação.
- `components/LoadScene.tsx`: a cena Three.js — baú, volumes, luzes, grade e órbita de câmera.
- `components/sceneGeometry.ts`: conversão de coordenadas e cores. **Funções puras, testadas.**

A tela vive na aba "Visualização 3D" de `features/load-planning/pages/PlanningPage.tsx`.

## Coordenadas: só conversão, nunca cálculo

O backend usa `x`=largura, `y`=altura, `z`=comprimento, origem no piso frente-esquerda (`docs/02`).
O Three.js também tem Y para cima, então os eixos coincidem. O que muda é a **âncora**: o backend dá o
canto do volume, o Three.js posiciona pelo centro — daí o `+ dimensão/2` em `itemBox`.

`docs/11` marca como `RISCO IDENTIFICADO` criar lógica geométrica no frontend, porque geraria
divergência entre o que se vê e o que o backend validou. Por isso `sceneGeometry.ts` só faz conversão
de unidade (cm→m) e de âncora. **Nenhuma decisão de encaixe, rotação ou colisão acontece aqui** — as
dimensões usadas são as já rotacionadas que vieram na resposta, não as originais do produto.

## Decisões de leitura

**A cor agrupa por ordem de ENTREGA, não de carregamento.** Quem olha a carga quer enxergar o que sai
junto na mesma parada. A sequência de carregamento aparece no detalhe do volume e na animação.

**O baú é renderizado por dentro** (`BackSide`): uma caixa sólida normal esconderia a carga da câmera.

**Animação (OC33)**: os volumes aparecem na ordem de carregamento; o que ainda não entrou fica
esmaecido em vez de sumir, para não dar a impressão de que o espaço está livre. Ao chegar ao fim, volta
sozinha para a carga completa. Há também um controle deslizante para percorrer passo a passo.

## Por que a cena não tem teste de render

WebGL não existe em jsdom, então renderizar `<Canvas>` no Vitest quebraria. A estratégia é: toda a
matemática mora em `sceneGeometry.ts` e é testada de verdade (inclusive um caso que confirma que o
volume fica dentro do baú); a cena em si é uma casca declarativa. Nos testes de `PlanningPage`, o
`LoadViewer` é mockado.

## Carregamento sob demanda

O three.js pesa ~830 kB no bundle. `PlanningPage` importa o viewer com `React.lazy`, então quem nunca
abre a aba 3D não baixa nada disso — o pacote principal fica em ~289 kB.

## Permissões

Mesma regra do plano: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem.
