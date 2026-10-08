# Carregamento

Checklist e estados do processo físico após aprovação do plano.

## Estado atual

`CONFIRMADO`: o módulo persiste uma sessão por plano aprovado e um item de
checklist para cada volume posicionado. O fluxo permitido é `PENDING ->
IN_PROGRESS -> FINISHED`; cada item avança de `PENDING` para `CHECKED` somente
durante `IN_PROGRESS`.

`CONFIRMADO`: a finalização exige todos os itens `CHECKED`. A fronteira pública
de `reference_service.py` libera `Trip SCHEDULED -> IN_ROUTE` somente quando a
sessão `FINISHED` pertence ao mesmo `load_plan_id`; sessão ausente, incompleta
ou de outro plano falha fechada.

## Autorização — OC66 (hierarquia atualizada na v1.2.0)

| Operação | `ADMIN` | `LOGISTICS_MANAGER` | `CHECKER` | `DRIVER` |
|---|---:|---:|---:|---:|
| Consultar sessão | Sim | Sim | Sim | Não |
| Criar sessão | Sim | Sim | Não | Não |
| Iniciar conferência | Sim | Não | Sim | Não |
| Conferir item | Sim | Não | Sim | Não |
| Finalizar carregamento | Sim | Não | Sim | Não |

`CONFIRMADO`: a autorização de perfil ocorre antes da consulta ao objeto, para
que acesso negado retorne `403 AUTH_FORBIDDEN` sem revelar a existência da
sessão ou do item. Acesso anônimo retorna `401 AUTH_INVALID_TOKEN`.

`CONFIRMADO`: não há autorização por objeto porque `loading_sessions` e
`loading_session_items` não possuem vínculo com um conferente. Para OC75 e
OC76, QR Code ou código de barras identifica o item, mas não autentica nem
autoriza o usuário; a confirmação deve reutilizar a permissão de
`ADMIN` ou `CHECKER` e as regras atuais do checklist.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Conferência por código — OC76

`CONFIRMADO`: `items[].code` expõe `loadx:loading-item:<id>` e
`POST /api/v1/loading-sessions/{id}/scan` confere o item para `ADMIN` ou `CHECKER`.
Formato, erros e integração OC75 estão em `docs/05-contratos-api.md`.
A operação reutiliza `change_item_status`, incluindo bloqueios de sessão/item,
com rejeição explícita de duplicatas. Código é identidade, não autorização.
