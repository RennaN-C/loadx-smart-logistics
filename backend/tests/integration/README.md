# Testes integration

Adicione aqui os testes correspondentes. Não use serviços externos reais.

`CONFIRMADO`: `test_authorization_matrix.py` cruza todas as operações protegidas com `ADMIN`, `LOGISTICS_MANAGER`, `CHECKER` e `DRIVER`. `test_openapi.py` garante que somente `/health` e `/api/v1/auth/login` permaneçam públicos no contrato atual.
