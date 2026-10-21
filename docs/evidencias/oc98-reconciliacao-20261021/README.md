# OC98 / #222 — reconciliação da PR #211

`CONFIRMADO`: validação de 21/10/2026 em ambiente local isolado, sem merge ou
deploy. Base integrada: `7ea5ca7` (OC90, após OC84/OC103/OC109). PR:
https://github.com/RennaN-C/loadx-smart-logistics/pull/211.

## Banco e preservação

- PostgreSQL 16 novo e exclusivo desta execução, sem reset de bases existentes.
- Caminho oficial: `20261020_0028` → `20261021_0029` → `20261021_0030`.
- `heads`, `current`, upgrade, downgrade até 0028, novo upgrade e `alembic check`
  executados. Head único, sem operações de atualização pendentes.
- Testes preservam perfis OC112, notificações/destinatários, outbox e a coluna
  de proveniência da entrega OC90 durante rollback da identidade.
- Revisões integradas permanecem inalteradas. Uso de identidade/dispositivos
  impede downgrade destrutivo, conforme ADR-038.

## Navegador real

`CONFIRMADO`: Chromium com API real, contas fictícias e PostgreSQL isolado:

- ADMIN e LOGISTICS_MANAGER: cadastro obrigatório de autenticador, QR SVG local,
  confirmação TOTP e dez códigos de recuperação; sessão restaurada após F5.
- Meu perfil mantém MFA/dispositivos, aparência e preferências da OC103 juntos.
- Opt-in por TOTP no segundo login, cookie HttpOnly/SameSite=Lax, login seguinte
  ainda exige senha. Esquecer dispositivo mantém sessão e volta a exigir MFA
  no próximo login.
- SMTP real contra Mailpit local exclusivo: mensagem multipart HTML/texto,
  redefinição efetiva, fragmento removido da URL e MFA preservado após reset.
- Capturas revisadas em 375, 768, 1280 e 1920 px, em claro e escuro; sem overflow
  horizontal. Não são usadas simulações de API ou registros fictícios de produção.

As imagens `perfil-<largura>-<tema>.png` mostram o perfil após autenticação.
`dispositivo-confiavel.png` mostra a gestão da confiança e
`recuperacao-concluida.png` mostra a confirmação sem token na URL.
QR, chave TOTP, códigos de recuperação, cookies e tokens **não** são capturados
nem versionados. Horários exibidos refletem o navegador local de validação.

## Qualidade e reprodução

`CONFIRMADO`: frontend completo com 971 testes/112 arquivos; ESLint, TypeScript,
build e budget 3D aprovados. `npm audit`: zero vulnerabilidades. Lockfiles do
backend instalados com `--require-hashes`, incluindo Pillow 13.0.0.

Executar a partir de `backend`, com `TEST_DATABASE_URL` apontando **somente para
um banco PostgreSQL 16 descartável exclusivo da suíte**, distinto do banco da
aplicação. A fixture existente recria o schema apenas desse banco de testes:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q tests --cov=app --cov-report=term
```

A partir de `frontend`, com Node 22:

```bash
npm ci --ignore-scripts
npm audit --audit-level=high
npm run lint
npm test -- --run
npm run build
```

Os resultados finais de Pytest/cobertura, Trivy, CI e SonarCloud são registrados
na PR #211, associados ao commit validado; este documento não substitui os checks.

## Limites de integração

`PENDENTE DE DEFINIÇÃO`: revisão humana e merge da PR #211. Nenhuma promoção ou
deploy nesta execução. SMTP/TLS público, NTP, custódia/backup da chave MFA,
homologação dos dispositivos confiáveis e worker da OC109 permanecem tarefas de
infraestrutura no ambiente aprovado. Não habilitar confiança por padrão sem essa
homologação. Bases experimentais antigas exigem análise específica, sem `stamp`,
reset ou perda de dados. As demais OCs seguem suas dependências e responsáveis;
não são implementadas nem declaradas concluídas nesta reconciliação.
