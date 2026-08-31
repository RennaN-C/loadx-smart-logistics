# Feature: load-visualization

Visualização 3D da carga (OC31), interação (OC32) e animação do carregamento (OC33).
Consome `GET /load-plans/{id}/visualization`.

## O que existe hoje

- `components/LoadViewer.tsx` (+ `.css`): busca a visualização, monta a cena, a legenda, o painel de
  detalhe do volume selecionado e os controles de animação.
- `components/LoadScene.tsx`: a cena Three.js — baú, volumes, luzes, grade e órbita de câmera.
- `components/CameraControls.tsx`: integra diretamente o `OrbitControls` oficial
  do Three.js ao ciclo de renderização do React Three Fiber.
- `components/sceneGeometry.ts`: conversão de coordenadas e cores. **Funções puras, testadas.**
- `components/truckShell.ts` (+ `TruckShellMesh.tsx`): o exterior do caminhão — cabine, chassi,
  para-choque e rodas. **Funções puras, testadas.**
- `components/productKind.ts`: classifica o produto pelo nome. **Função pura, testada.**
- `components/cargoTexture.ts`: a superfície dos volumes por tipo, desenhada em canvas.
- `components/cameraViews.ts`: os cinco ângulos prontos. **Funções puras, testadas.**

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

## O tamanho de cada volume vem do produto, não é fixo

`itemBox` usa `widthCm`, `heightCm` e `lengthCm` **do item**, que chegam já rotacionados pelo
backend. Volume grande é grande na cena. Se todos os pacotes aparecem do mesmo tamanho, é porque
foram CADASTRADOS do mesmo tamanho — o `sceneGeometry.test.ts` cobre isso: 20×15×30 e 80×60×120
produzem caixas com quatro vezes de diferença.

## A aparência sai do tipo do produto

`productKind.ts` lê o NOME cadastrado e classifica: TV, geladeira, fogão, lavadora, micro-ondas ou
caixa. Uma TV vira tela escura com reflexo; uma geladeira, porta clara com puxador; um fogão, tampo
preto com quatro bocas. O que não é reconhecido cai em papelão, que é o certo.

`PENDENTE DE DEFINIÇÃO`: o produto **não tem campo de categoria** no backend. Enquanto não tiver, a
classificação sai de palavra-chave sobre o nome — heurística assumidamente falível: "TV 50" acerta,
"modelo XPT-42" não. Quando a equipe adicionar `category`, `productKind.ts` passa a ler o campo e as
palavras-chave viram só o fallback. A classificação casa por **palavra inteira** e ignora acento e
caixa, senão "Estante" viraria TV.

**A forma continua sendo a caixa que o otimizador reservou.** Uma TV é um paralelepípedo com cara de
TV, não um modelo de TV. Mudar a geometria faria a tela mentir sobre o espaço ocupado, que é a razão
de ela existir (`docs/11`).

## Superfície desenhada em canvas, não fotografada

Cada tipo tem seis faces pintadas em tempo de execução, com a face do produto voltada para a porta
do baú — que é de onde a câmera olha. Custo: **2,2 KiB gzip** no chunk. Um jogo de fotos de TV,
geladeira e fogão comeria a folga inteira do orçamento, a mesma conta que levou o caminhão a ser
construído em vez de importado. Cada tipo novo custa algumas dezenas de linhas e zero byte de asset.

### O que faz a caixa parecer caixa

Quatro coisas, e nenhuma delas é a cor:

- **Cinta de amarração** em duas faixas nas quatro laterais, com brilho de plástico e a sombra que
  ela projeta no papelão logo abaixo. É o detalhe que mais separa carga paletizada de "cubo marrom".
- **Vinco com bisel**: depois da faixa escura da quina vem uma faixa CLARA. Caixa de verdade não tem
  quina viva, e é esse par escuro-claro que o olho lê como aresta arredondada pegando luz.
- **Três tons de papelão**, escolhidos pelo código do produto. Uma pilha do mesmo item continua
  uniforme — como fica no caminhão —, mas pilhas diferentes não saem todas iguais, que é o que mais
  entrega uma cena sintética.
- **Relevo**: a mesma imagem serve de `bumpMap`. A fibra, a fita e a cinta deixam de ser desenho e
  passam a pegar luz como superfície.

A textura subiu para 512px porque a câmera CHEGA PERTO: na vista interna um volume ocupa meia tela,
e a 256 a fibra virava borrão. Junto veio filtragem anisotrópica, sem a qual a face vista de
esguelha — a maioria numa carga empilhada — vira mancha.

Medido no navegador sobre o código real, já que jsdom não tem canvas: os três tons ficam em 132, 140
e 151 de brilho médio, separados o bastante para distinguir sem destoar; a granulação subiu de 67
para ~100 níveis de variação; a cinta contrasta 70 níveis contra o papelão; e a sequência do bisel
sai 102 na borda, 149 logo dentro e 142 no meio. O brilho médio de cada tipo bate com o que ele
representa — TV, tampo de fogão e micro-ondas entre 25 e 41, geladeira e lavadora entre 184 e 207.

O tom entra na chave do cache só para o papelão. Eletrodoméstico tem cor própria e ignora o tom;
sem essa normalização, uma geladeira cujo código caísse no tom 2 geraria uma segunda leva idêntica
na memória da placa.

O cache é por TIPO e vive enquanto a aba viver. O teto é a quantidade de tipos, constante, e não
cresce com o tamanho da carga. Liberar num efeito criava problema pior: o StrictMode monta,
desmonta e remonta, então o descarte rodava no meio e deixava material apontando para textura já
liberada.

**A cor da entrega migrou para a ARESTA do volume.** Tingir a superfície deixaria a TV laranja, e TV
laranja não é TV. O contorno que já existia para separar volumes encostados passou a carregar a cor
da legenda — o agrupamento por entrega continua legível sem falsear o produto.

O controle **"Realista"** desliga tudo isso e devolve as cores chapadas, para comparar.

## Por que o caminhão é desenhado em código, e não importado

A opção óbvia seria baixar um `.glb` de caminhão pronto. Foi medido e descartado: um modelo tem
proporção **fixa**. O caminhão de referência avaliado tinha razão comprimento/largura de 0,62 e
comprimento/altura de 1,08 — um baú real fica em 2,50 e 2,31. Esticá-lo até as medidas cadastradas
deformaria a cabine e as rodas junto, e a tela inteira existe para transmitir precisão dimensional:
um caminhão de 9 m e um de 4 m precisam parecer diferentes.

Então `truckShell.ts` deriva o exterior das medidas do cadastro. Comprimento, largura e altura do baú
mandam em tudo que se apoia neles. São constantes apenas as medidas de chassi que a API não fornece e
que não afetam a carga: altura do piso (1,15 m), raio de roda (0,50 m), comprimento e teto da cabine.
Um baú de 9 m ganha eixo tandem; um de 4 m não. A cabine tem teto travado em 2,55 m, então um baú
alto sobe sem esticar a cabine junto.

Isso **não** viola a regra de `docs/11`: nenhuma dessas medidas entra em cálculo de encaixe. Elas
posicionam desenho. As coordenadas dos volumes continuam intocadas — a carga inteira é levantada por
um `<group position={[0, deckHeight, 0]}>`, não por conversão item a item.

Custo: **0,7 KiB gzip**. Um `.glb` custaria centenas de KB de download mais o `GLTFLoader`, que
sozinho consumiria quase toda a folga do orçamento de bundle.

O exterior pode ser desligado no controle "Mostrar caminhão", para inspecionar a carga sem a cabine
e as rodas no caminho.

## Passo a passo do carregamento (OC33)

Um passo é **um volume**. O volume do passo desliza da porta até a posição, e os que ainda não
entraram ficam esmaecidos em vez de sumir — sumindo, o espaço deles pareceria livre.

**A câmera não se mexe sozinha.** Quem confere precisa manter o próprio ângulo, então o movimento do
volume é o único sinal de qual está entrando agora. Por isso a entrada é animada: sem ela, avançar
um passo com a câmera parada seria uma caixa aparecendo do nada.

O progresso da animação vive num `ref`, não em estado: animar por estado dispararia um render do
React a cada quadro, e quem já está dentro do laço do Three não precisa disso.

Avançar o passo **seleciona** o volume, então o painel lateral de detalhe acompanha sem código
extra. As setas ← e → percorrem a sequência, e só respondem com o passo a passo aberto — fora dele
elas sequestrariam a rolagem da página.

Ao chegar ao último, a reprodução para no volume final em vez de voltar à carga completa: quem
chegou ao fim quer ver a carga fechada, não recomeçar.

## Cinco ângulos prontos

Girar até achar o ponto de vista certo é trabalho que a tela pode poupar: conferir uma carga tem
sempre as mesmas perguntas, e cada uma tem um ângulo que a responde. **Lateral** mostra as camadas e
a altura de empilhamento; **topo**, o aproveitamento do piso; **traseira** é o que o conferente vê
ao abrir a porta; **interna** põe a câmera dentro do baú, olhando para o fundo — a única que não
mira o centro.

Tudo derivado das medidas: um baú de 9 m precisa de mais recuo que um de 4 m, e a mira sobe junto
com a carga quando o exterior do caminhão está ligado.

## Os indicadores vêm do backend, não daqui

Ocupação, peso e contagens são os números que o backend já publicou no plano, repassados pela
`PlanningPage`. O viewer **não recalcula**: refazer a conta aqui abriria divergência entre o que se
lê na tela e o que foi validado no cálculo (`docs/11`).

## O que ainda depende do backend

O nível de organização da carga — volumes iguais em colunas e camadas alinhadas, formando blocos —
**não é da visualização, é do algoritmo de empacotamento**. A engine atual (`heuristic-v1`) usa
first-fit sobre pontos candidatos; nenhum viewer transforma isso em parede organizada. Uma
estratégia de *wall building* no otimizador é o que muda essa imagem, e mora em
`backend/app/modules/load_planning/optimizer`.

Pelo mesmo motivo não existe contagem de "blocos": o backend não tem esse conceito, e derivá-lo aqui
agrupando volumes vizinhos seria lógica geométrica no frontend, exatamente o que `docs/11` marca
como `RISCO IDENTIFICADO`.

## O piso não pisca mais: superfícies coplanares

Duas superfícies no mesmo plano disputam o mesmo valor de profundidade, e a placa de vídeo alterna
entre elas a cada quadro. Ao girar a câmera isso aparece como piscar. A cena tinha **três** pares
assim:

1. A caixa sólida do baú e uma segunda caixa em modo arame, com geometria e posição **idênticas**.
2. O topo do chassi e o piso do baú, os dois exatamente em `DECK_HEIGHT`.
3. O piso do baú e a base de todo volume apoiado nele — que é a maioria da carga.

As correções, na mesma ordem: o contorno virou `edgesGeometry`, que desenha as 12 arestas e não tem
superfície para disputar nada (de quebra sumiram as diagonais que o modo arame desenhava em cada
face); o chassi desceu `CHASSIS_CLEARANCE`; e o **desenho** do baú afunda `SHELL_SINK` — os volumes
não se movem, quem desce é a casca.

O contorno dos volumes tinha o mesmo problema em menor escala: era uma caixa 0,1% maior, o que dá
dois décimos de milímetro num volume de 40 cm, dentro da margem de erro do buffer. Virou aresta
também.

Depois apareceu o mesmo defeito na FRENTE, e lá eram **três** superfícies no mesmo plano de uma vez:
a face dianteira da cabine, a traseira do para-choque e a dianteira do chassi, todas em
`z = -CAB_LENGTH`. O chassi ainda repetia a dose atrás, com a ponta traseira na face do baú. As
pontas do chassi passaram a recuar `END_CLEARANCE`, e o para-choque entra alguns centímetros DENTRO
da cabine em vez de encostar nela — sólidos que se interpenetram não brigam, sólidos que se tocam
brigam.

No caminho apareceu outro defeito: o para-brisa estava 3 cm para DENTRO da cabine, ou seja, a
cabine tapava o próprio vidro e o detalhe nunca foi visto. Agora é saliente.

Junto disso, a câmera passou a usar `near: 0.05` e `far: 200`. O padrão vai de 0,1 a 1000 e
desperdiça precisão de profundidade num cenário de vinte metros — apertar o alcance é o que dá
margem para superfícies próximas conviverem.

## Por que a cena não tem teste de render

WebGL não existe em jsdom, então renderizar `<Canvas>` no Vitest quebraria. A estratégia é: toda a
matemática mora em `sceneGeometry.ts` e é testada de verdade (inclusive um caso que confirma que o
volume fica dentro do baú); a cena em si é uma casca declarativa. Nos testes de `PlanningPage`, o
`LoadViewer` é mockado.

## Carregamento sob demanda

O chunk 3D tem cerca de 828 kB minificado e 218 kB com gzip. `PlanningPage`
importa o viewer com `React.lazy`, então quem nunca abre a aba 3D não baixa esse
conteúdo. Caddy aplica compressão e cache imutável ao asset versionado.

`CONFIRMADO`: o build falha se o chunk `LoadViewer` ultrapassar 250 KiB com gzip.
O limite padrão não comprimido do Vite foi ajustado para 850 kB porque a métrica
de rede comprimida e o carregamento sob demanda representam melhor o impacto
real. Drei foi removido: o único uso era `OrbitControls`, agora integrado
diretamente, eliminando 48 pacotes e a dependência depreciada
`three-mesh-bvh@0.7`.

## Permissões

Mesma regra do plano: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem.
