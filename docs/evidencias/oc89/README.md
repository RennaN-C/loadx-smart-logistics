# OC89 — evidências da distribuição multi-caminhão

`CONFIRMADO`: Chromium 151 com API FastAPI e PostgreSQL 16 locais, base
`desenvolvimento` com OC87/88/112 e dados exclusivamente fictícios, isolados em
`loadx_oc89_browser`. Nenhum deploy ou banco existente foi alterado.

## Verificação

- Login real do gestor e `POST /load-distributions/optimize` 201 com três volumes
  físicos distribuídos exatamente entre três caminhões (necessidade completa).
- Troca entre dois veículos consultando seus próprios IDs no endpoint de cena.
- Resumo e cena nas larguras 375, 768, 1280 e 1920, em claro e escuro: 16 cenários.
- Oito capturas abaixo, revisadas visualmente; sem overflow horizontal da página.
- Navegação para Produtos, retorno pela lista e atualização do navegador sem
  executar optimize novamente. Aprovação parcial e total preservam a fronteira OC90.

| Conteúdo | Claro desktop | Escuro desktop | Claro mobile | Escuro mobile |
|---|---|---|---|---|
| Resumo | [1280](resumo-light-1280.png) | [1280](resumo-dark-1280.png) | [375](resumo-light-375.png) | [375](resumo-dark-375.png) |
| Cena selecionada | [1280](cena-light-1280.png) | [1280](cena-dark-1280.png) | [375](cena-light-375.png) | [375](cena-dark-375.png) |

`CONFIRMADO`: os testes Vitest também cobrem 1/2/3 caminhões, identidade de volumes,
recuperação, erros/retry, aprovação/cancelamento/reprocessamento e catálogo de
permissões. PostgreSQL cobre snapshots e recuperação das versões reprocessadas.

`PENDENTE DE DEFINIÇÃO`: validação humana do fluxo e dos dois temas com dados
representativos da operação. Não há garantia de otimização global; a interface
não inicia operação multi-caminhão antes da OC90. Capturas não comprovam todos
os critérios WCAG; teclado e foco também devem ser verificados na revisão humana.
