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



`CONFIRMADO`: test_multi_truck_flow.py executa OC90 usando optimize real, duas
partes forçadas fisicamente, carregamentos/checklists disjuntos, falha de B antes
do carregamento, conclusão independente de A, retry de B, recomposição única do
pedido, comprovantes, PDFs e auditoria. pypdf é dependência somente de testes
para verificar conteúdo e identidades no PDF real, além do MIME/magic. O teste
legado test_complete_flow.py mantém seu fluxo anterior sem adaptações.

Em backend, com TEST_DATABASE_URL exclusivo, execute:

```bash
python -m pytest -q tests/integration/test_multi_truck_operations.py tests/integration/test_multi_truck_concurrency.py tests/e2e
```

Concorrência usa transações PostgreSQL independentes, barreira e mapas de
identidade intencionalmente obsoletos; verifica um histórico agregado e conclusões
independentes. Integração também testa escrita direta, rollback e downgrade seguro.

`CONFIRMADO`: cenários, reprodução, resultados e inventário da OC90 em
[evidências operacionais](../../../docs/evidencias/oc90/README.md).
