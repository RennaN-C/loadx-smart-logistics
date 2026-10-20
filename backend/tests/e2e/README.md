# Testes e2e

`CONFIRMADO`: `test_complete_flow.py` cobre cadastro, pedido, planejamento,
aprovação, loading, viagem, entrega, ocorrência e download dos dois relatórios.

Execute com o mesmo PostgreSQL 16 exclusivo da suíte de integração:

```powershell
python -m pytest -q tests/e2e
```

Não use serviços externos reais.

`CONFIRMADO`: o fluxo utiliza Sessions ligadas ao Engine para comprovar commit
durável antes do mock (OC84). A fixture compartilhada valida PostgreSQL 16 e banco
exclusivo loadx_test, limpando somente os dados desse ambiente. Os cenários de
savepoint/rollback continuam na integração e nunca autorizam tentativa prematura.
