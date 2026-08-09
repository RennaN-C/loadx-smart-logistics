# Serviços

Cliente HTTP, tratamento padronizado de erros e adaptadores do navegador.

A URL da API vem de `VITE_API_URL`. Não espalhe chamadas Axios diretamente pelas páginas.

`CONFIRMADO`: o cliente envia cookies com `withCredentials`, injeta
`X-CSRF-Token` somente em métodos inseguros e limpa o token em memória quando a
sessão é invalidada. Credenciais de autenticação não usam Web Storage.
