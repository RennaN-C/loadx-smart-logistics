# Feature: reports

Relatórios e indicadores de pedidos (`OC35`, manutenção #206), em `/reports`.

## O que existe hoje

- `reportMetrics.ts`: os indicadores. **Funções puras, testadas.**
- `hooks/useOrderReport.ts`: pagina a coleção de pedidos e resolve os nomes dos clientes.
- `components/DistributionBars.tsx`: barras de distribuição, reaproveitadas por situação e prioridade.
- `pages/ReportsPage.tsx` (+ `.css`).

## Os números vêm dos pedidos, e só deles

Não existe endpoint de agregação no backend — o mesmo motivo que levou o dashboard (`OC25`) a
contar pelo `total` do envelope de paginação. A diferença é que aqui os indicadores exigem as
**linhas**, não só a contagem, então a tela pagina a coleção e agrega no cliente.

`CONFIRMADO`: os indicadores desta tela agregam somente pedidos por
`useOrderReport`. `GET /trips` já existe e é consumido por `tripsApi.ts`, mas
seus dados ainda não entram nesses indicadores. Não há listagem pública de
planos nem agregação de ocupação da frota.

`CONFIRMADO`: `reportsApi.ts` e `ReportDownloadButton` também oferecem download
dos PDFs gerados pelo backend para carregamento e viagem, com permissões
próprias. Os PDFs não são gerados pelos indicadores desta tela.

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
403 em `/customers`. A consulta de clientes não é disparada para CHECKER. Falha na resolução de
nomes dos perfis autorizados é isolada; o resto do relatório continua de pé.

## Volumes físicos e limites — #206

`CONFIRMADO`: `itemCount` conta linhas; `volumeCount` vem de `volume_count` no
resumo de pedidos e representa a soma das quantidades físicas. KPI de volumes
em aberto, tabela de atrasados e agregação por cliente usam somente esse campo.
Payload legado sem o campo não é tratado como zero nem substituído por linhas:
os totais afetados aparecem como “—”, com alerta explícito.

`CONFIRMADO`: a apuração continua limitada a até 1.000 pedidos, com ressalva
permanente e aviso de registros não apurados. Data de referência permanece
congelada por consulta; a paginação não cria snapshot transacional no servidor.
Encerrados significa entregues/cancelados; volumes em aberto não afirmam que
pedidos já em trânsito ainda precisam carregar.

`CONFIRMADO`: a identidade visual usa os tokens LoadX, hierarquia e superfícies
da área administrativa, tabelas responsivas com foco/rolagem por teclado e nomes
longos legíveis. Fonte e escopo dos indicadores são independentes da OC69.
PDFs de viagem/carregamento e suas permissões próprias permanecem intactos.
