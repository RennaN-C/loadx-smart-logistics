# API

Agrega routers públicos da versão `/api/v1`.

Esta pasta não implementa regras. Cada módulo expõe seu próprio router e o agregador apenas registra as rotas.

O agregador documenta no OpenAPI o envelope compartilhado para erros inesperados `500` em todas as rotas de negócio.
