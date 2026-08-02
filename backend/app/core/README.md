# Core

Configurações globais, segurança, logging e exceções compartilhadas.

Não coloque regras de caminhão, pedido ou carga aqui. O core deve conhecer infraestrutura, não detalhes de negócio.

## Arquivos

- `config.py`: variáveis de ambiente e configurações globais.
- `exceptions.py`: handlers globais e serialização de erros de validação HTTP.
- `responses.py`: construção compartilhada do envelope de erro HTTP.
- `security.py`: hash de senha e JWT usados pela autenticação.
