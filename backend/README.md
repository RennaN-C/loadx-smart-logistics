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

## Primeiro administrador

Depois de aplicar as migrations e antes de expor a API, crie o primeiro administrador com o comando interativo:

```bash
python -m app.modules.auth.bootstrap
```

Com Docker Compose, execute a partir da raiz sem publicar a porta do backend:

```bash
docker compose run --rm backend python -m app.modules.auth.bootstrap
```

A senha é solicitada de forma oculta e não deve ser informada em argumento, `.env`, seed ou log. O comando recusa nova execução quando o banco já possui qualquer usuário.
