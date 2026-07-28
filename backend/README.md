# Backend

API FastAPI do LoadX.

## Organização

- `app/core`: configurações e segurança.
- `app/database`: conexão, base e sessão.
- `app/api`: agregação de rotas.
- `app/modules`: módulos de negócio.
- `app/integrations`: IA e WhatsApp por adaptadores.
- `app/shared`: tipos e utilitários realmente compartilhados.
- `migrations`: alterações versionadas do banco.
- `tests`: testes unitários e integrados.

## Regra de camadas

```text
router -> service -> repository -> database
              |
              -> domain/optimizer
```

Não coloque regras de negócio em `router.py` nem SQL direto nos serviços.
