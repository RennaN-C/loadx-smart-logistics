# Shared

Tipos, erros e utilitários usados por mais de um módulo.

Só mova algo para `shared` quando houver reutilização real. Evite transformar esta pasta em um depósito de código sem dono.

## Validade documental OC101/OC102

`CONFIRMADO`: document_validity.py contém DocumentDates, protocolo de documento,
normalização UTC e status temporal (VALID/EXPIRING/EXPIRED/NOT_YET_VALID/
SUPERSEDED). Alertas até 30 dias e vencimento exclusivo são compartilhados por
caminhões e motoristas. Ownership SQL, políticas e RBAC continuam nos módulos.

## Busca OC95

`CONFIRMADO`: search.py centraliza trim, teto de 120 caracteres e escape literal
de LIKE. Repositories mantêm a whitelist dos campos; core/search.py valida HTTP
sem introduzir FastAPI no helper puro. Não há busca por campos pessoais proibidos.
