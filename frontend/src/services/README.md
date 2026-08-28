# Serviços

Cliente HTTP, tratamento padronizado de erros e adaptadores do navegador.

A URL da API vem de `VITE_API_URL`. Não espalhe chamadas Axios diretamente pelas páginas.

`CONFIRMADO`: o cliente envia cookies com `withCredentials`, injeta
`X-CSRF-Token` somente em métodos inseguros e limpa o token em memória quando a
sessão é invalidada. Credenciais de autenticação não usam Web Storage.

## Mensagens de erro

`validationErrors.ts` transforma o 422 do backend em texto que diz QUAL campo está errado. A
informação sempre esteve na resposta — o envelope traz `details` com `{ field, message, type }` por
problema —, mas a tela só mostrava o `message` de cima: "Os dados informados são inválidos", que não
ajuda ninguém a consertar nada.

O `message` de dentro do detalhe vem em inglês, do Pydantic. Por isso a tradução sai do `type`, que
é estável, e não do texto. O limite numérico é a exceção: só aparece na mensagem em inglês
("Input should be greater than 0"), então é lido de lá.

`items.0.quantity` vira "Quantidade (item 1)": o índice sai do caminho e a busca pelo rótulo usa o
caminho sem ele, senão cada posição da lista exigiria uma entrada própria no mapa. Campo sem rótulo
cai no nome cru, que ainda é melhor que nada.

`apiErrorMessages.ts` é o último degrau, comum a todas as telas: primeiro o 422 detalhado, depois os
códigos que não pertencem a domínio nenhum (rede, sessão, permissão, excesso de requisições), por
último o texto que o backend mandou. Cada feature continua dona dos códigos dela — quem sabe
explicar `TRUCK_PLATE_ALREADY_EXISTS` é a tela de caminhões.
