# Scripts do frontend

- `check-bundle-budget.mjs`: valida o tamanho gzip do chunk 3D depois do build.

Scripts desta pasta devem ser determinísticos, não acessar rede e falhar com
código diferente de zero quando o gate não for atendido.
