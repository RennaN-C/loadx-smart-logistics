# Modelos 3D

## `truck-cab-daf.glb`

Cabine do caminhão usada na visualização de carga. É a **única** geometria da
cena que vem de arte pronta.

`CONFIRMADO`: ela pôde vir de modelo justamente porque já era constante.
`CAB_LENGTH` e `CAB_TOP` (`truckShell.ts`) nunca saíram da API — a cabine não
carrega informação sobre o espaço de carga. Baú, chassi e rodas continuam
derivados do cadastro do caminhão, como `docs/11` exige.

`RISCO IDENTIFICADO`: trocar o **baú** por arte faria um baú de 6 m e uma
carreta de 12 m aparecerem iguais na tela, e a visualização passaria a mentir
sobre o espaço disponível. O baú do modelo original foi descartado por isso.

### Como foi gerado

A partir de `Truck_DAF/OBJ/truck_daf.obj`, com o conversor do próprio projeto:

```bash
python frontend/scripts/obj2glb.py truck_daf.obj truck-cab-daf.glb \
  Plane Plane.001 Cube_Cube.006 Cube.001_Cube.007 \
  light_ban_4.001_Cylinder.004 light_ban_4_Cylinder.003 light_ban_3_Cylinder.002 \
  ban_depan_Cube.003 truck_daf.001_Cube.004 \
  light_ban_2_Cylinder.001 light_ban_Cylinder \
  truck_daf.003_Cube.005 truck_daf.002_Cube.001
```

Os objetos listados são descartados: dois planos de cenário, o baú e o bogie da
carreta, as rodas e o chassi — tudo isso o projeto já desenha a partir das
medidas reais. Sobram a cabine e o escapamento.

| | OBJ original | GLB publicado |
| --- | --- | --- |
| tamanho | 35,3 MB | 1,32 MB (759 KB gzip) |
| triângulos | ~513 mil | 71.472 |

`CONFIRMADO`: o GLB não tem coordenadas de textura. O MTL original traz os 14
materiais no mesmo cinza `0.64` e **nenhum** `map_Kd`, então as PNGs que
acompanham o pacote não estavam ligadas a nada. As cores saem da paleta por
nome de material dentro do conversor (`col_body`, `col_kaca` = vidro,
`col_ban` = pneu, `col_pelek` = roda). Gravar UV custaria 8 bytes por vértice
para carregar zero informação.

### Dimensões naturais

Depois da normalização do conversor — X centrado em zero, Y zerado na base,
Z começando em zero, frente apontando para +Z:

| eixo | medida |
| --- | --- |
| largura total (com retrovisores) | 3,681 |
| largura do corpo (sem retrovisores) | 3,25 |
| altura | 4,391 |
| comprimento | 2,945 |

`truckCabModel.ts` escala pelo **corpo**, não pelo total: 95% dos vértices
cabem em 3,25 e o resto são os braços dos retrovisores. Escalar pelo total
deixaria a cabine mais estreita que o próprio caminhão.

### Procedência

`PENDENTE DE DEFINIÇÃO`: o pacote recebido (`84-truck_daf/Truck_DAF`) não traz
arquivo de licença nem de atribuição. Antes de a v1.1.0 ir a público é preciso
confirmar a origem e registrar a atribuição exigida, se houver.
