# Feature: dashboard

Painel inicial (OC25). É a rota raiz `/`, no lugar do placeholder da OC23.

## O que existe hoje

- `pages/DashboardPage.tsx` (+ `.css`): contadores por recurso e os pedidos mais recentes.
- `hooks/useDashboardTotals.ts`: busca os números e a lista recente.

## Os números vêm do envelope de paginação

**Não existe endpoint de agregação no backend.** Os contadores usam o `total` que a ADR-017 já devolve
em toda coleção: pedindo `page_size=1`, o número é exato e a resposta é mínima — sem baixar a coleção
inteira só para contar.

Os pedidos recentes usam a primeira página com `page_size=5`. Como `sort_order` já é `desc` por
`created_at` por padrão, a primeira página **é** a dos mais recentes, sem precisar de parâmetro novo.

## Falha parcial não derruba o painel

Cada recurso é buscado de forma independente. `CHECKER` não lê clientes nem motoristas, e um 403 ali
não pode zerar a tela: o contador que falhou vira "—", os outros continuam válidos, e a página avisa
que alguns números não carregaram. Para quem não lê dado pessoal, esses contadores nem são pedidos.

## Fora de escopo

`CONFIRMADO`: `/reports` já apresenta indicadores de pedidos e o backend gera
PDFs de carregamento e viagem. Ocupação média da frota e evolução no tempo
continuam futuras; não há endpoint de agregação geral. O painel do motorista
já usa `DriverTrips` para listar suas viagens.
