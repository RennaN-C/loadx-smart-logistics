# Integração com WhatsApp

Começa com um provider mock ou simulador. A integração real deve seguir a mesma interface.

Responsabilidades:

- receber mensagem;
- identificar motorista;
- interpretar comando;
- chamar service público;
- responder resultado;
- registrar auditoria.

Não acessa o banco diretamente.

`CONFIRMADO`: o fluxo controlado usa `MockWhatsAppProvider`, resolve motorista
por telefone, exige usuário `DRIVER` ativo e delega mudanças exclusivamente ao
`TripService`. Comandos desconhecidos, estado inválido e identificação ambígua
falham sem alterar viagem ou entrega.

`CONFIRMADO`: `POST /api/v1/messages/interpret` é um simulador interno protegido
para `ADMIN` e `LOGISTICS_MANAGER`. `driver_phone` identifica somente o motorista
representado na simulação e não autentica a chamada. Webhook, autenticação real
do WhatsApp e provider externo permanecem fora do MVP.
