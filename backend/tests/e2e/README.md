# Testes e2e

`CONFIRMADO`: `test_complete_flow.py` cobre cadastro, pedido, planejamento,
aprovação, loading, viagem, entrega, ocorrência e download dos dois relatórios.

Execute com o mesmo PostgreSQL 16 exclusivo da suíte de integração:

```powershell
python -m pytest -q tests/e2e
```

Não use serviços externos reais.
