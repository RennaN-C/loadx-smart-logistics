# Feature: reports

Tela de indicadores (`OC35`), em `/reports`.

## O que existe hoje

- `reportMetrics.ts`: os indicadores. **Funções puras, testadas.**
- `hooks/useOrderReport.ts`: pagina a coleção de pedidos e resolve os nomes dos clientes.
- `components/DistributionBars.tsx`: barras de distribuição, reaproveitadas por situação e prioridade.
- `pages/ReportsPage.tsx` (+ `.css`).

## Os números vêm dos pedidos, e só deles

Não existe endpoint de agregação no backend — o mesmo motivo que levou o dashboard (`OC25`) a
contar pelo `total` do envelope de paginação. A diferença é que aqui os indicadores exigem as
**linhas**, não só a contagem, então a tela pagina a coleção e agrega no cliente.

Só os pedidos entram. `load-plans` e `deliveries` **não têm endpoint de listagem** (apenas
`GET /{id}`), então não há como apurar ocupação média de caminhão, viagens no período ou entregas
por motorista sem inventar contrato. Quando a equipe expuser `GET /load-plans` e `GET /trips`,
esses indicadores entram aqui.

## Por que a data de referência entra por parâmetro

"Atrasado" depende de agora, e `new Date()` solto dentro do cálculo tornaria o teste dependente do
relógio e do fuso de quem roda. A referência é congelada uma vez por carga e passada para as
funções puras, como já acontece em `orders/components/orderDateTime.ts`. De quebra isso conserta um
problema de leitura: com a data recalculada a cada render, a contagem de atrasados poderia deixar
de bater com a lista logo abaixo dela enquanto a pessoa lê a tela.

## Teto de páginas

`MAX_PAGES = 10` a 100 por página: mil pedidos. Sem filtro server-side (`D12`), paginar a coleção
inteira é a única saída. Passando do teto a tela **avisa quantos ficaram fora**, em vez de mostrar
um número truncado como se fosse o total.

## Perfis

Pedidos são lidos por `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER`. Clientes, não: o conferente recebe
403 em `/customers`. O erro é isolado — o relatório por cliente simplesmente não aparece para ele,
e o resto da tela continua de pé. Mesmo tratamento do dashboard.

## Identidade visual

As medidas repetem as do dashboard (`.kpi`) e das tabelas do planejamento (`.plan-table`) de
propósito, não por coincidência: cartão, rótulo em mono de 9.5px, número em mono de 1.9rem, barra
de 8px com trilho em `--line` e preenchimento em `--accent`. Conferido lado a lado com os valores
computados dos dois: idênticos.

A cor só carrega significado em dois lugares — verde no entregue, cinza no cancelado na barra de
situação, e vermelho no número de atrasados. O resto é acento, para o destaque continuar
destacando.
