# Empresa standalone — OC91

`CONFIRMADO`: GET/PUT `/company-profile`, somente ADMIN ativo. GET retorna null
quando não cadastrado. PUT substitui nome empresarial/de exibição e opcionais
CNPJ, telefone, e-mail e referência HTTPS de logotipo. Vazio opcional vira null.
Persistência singleton e auditoria atômicas; sem uploads, segredos ou tenancy.
Ver [ADR-035](../../../../docs/decisions/ADR-035-configuracoes-institucionais-standalone.md).
