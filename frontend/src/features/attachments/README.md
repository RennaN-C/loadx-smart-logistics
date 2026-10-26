# Anexos contextuais — OC110

`CONFIRMADO`: AttachmentPanel reutiliza o contrato paginado OC110 e mantém
event_id durante retries. Pedidos abrem modal pelo card (conferente só consulta).
Viagem abre modal com seleção de viagem, entrega e ocorrência; ocorrências vêm
do endpoint existente autorizado. Dados são carregados sob demanda.

PNG/JPEG até 5 MiB, seleção/envio, download autenticado como Blob, confirmação de
remoção lógica, estado removido sem download, paginação, loading/erro/vazio.
Backend continua fonte de autorização, MIME real e checksum. Nunca monta URL
de storage, nunca armazena bytes em localStorage nem usa URLs externas.
A chave do evento muda quando o usuário seleciona outro arquivo.

`CONFIRMADO`: helper protectedDownload conserva erros JSON retornados como
Blob, também reutilizado por relatórios com contratos anteriores preservados.
Storage real de produção e novos tipos MIME dependem das decisões da ADR-033.
