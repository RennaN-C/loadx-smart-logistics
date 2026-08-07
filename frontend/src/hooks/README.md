# Hooks compartilhados

Hooks usados por mais de uma feature. Hook de uma feature só permanece dentro dela
(`features/auth/hooks/useAuth.ts`, por exemplo).

## O que existe hoje

- `useResourceList.ts`: carrega uma lista completa da API e expõe `status` / `items` / `error` /
  `refetch`. Nasceu como `useTrucks` na OC26, virou genérico na OC28 quando o mesmo código já
  existia em quatro cadastros.

  A função passada precisa ser uma **referência estável** — passar a função exportada do módulo de
  API (`listTrucks`, `listCustomers`, …) já resolve. Uma arrow inline recriada a cada render faria o
  `useEffect` disparar em laço.
