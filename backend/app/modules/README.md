# Módulos de negócio

Cada subpasta representa uma capacidade do LoadX. Mantenha limites claros e prefira chamadas entre services em vez de acessar modelos alheios diretamente.

## Núcleo SaaS

- `organizations/`: organizações, memberships, convites e concessão do proprietário geral. A fase 1 cria o registro e contexto de sessão; não libera ainda uma segunda organização operacional.

Os módulos logísticos permanecem single-tenant até a conclusão do scoping completo, das FKs compostas e dos testes de isolamento.
