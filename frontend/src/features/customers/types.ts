/**
 * A listagem devolve um resumo (`CustomerListRead`), sem documento, telefone,
 * endereço nem observações — dado pessoal só sai no detalhe. Por isso os dois
 * tipos: o card usa `CustomerListItem`, o formulário exige `Customer` completo,
 * buscado por `GET /customers/{id}` na hora de editar.
 */
export interface CustomerListItem {
  id: string;
  name: string;
  city: string;
  /** UF com 2 letras, normalizada em maiúsculas pelo backend. */
  state: string;
  createdAt: string;
}

export interface Customer extends CustomerListItem {
  document: string;
  phone: string | null;
  address: string;
  notes: string | null;
}

export interface CustomerInput {
  name: string;
  document: string;
  phone: string | null;
  address: string;
  city: string;
  state: string;
  notes: string | null;
}

export type CustomerUpdateInput = Partial<CustomerInput>;

/**
 * Endereço devolvido pela consulta de CEP (OC62).
 *
 * `CONFIRMADO`: a resposta de `GET /customers/cep/{cep}` é o próprio
 * `ViaCEPAddress`, SEM envelope. Um CEP municipal pode não ter rua, bairro ou
 * complemento — por isso os três são anuláveis. Cidade e UF são obrigatórios.
 *
 * Não existe campo `cep` em `Customer`: isto não é persistido, é só auxílio de
 * preenchimento.
 */
export interface CepAddress {
  /** Oito dígitos, sem hífen, igual ao que foi consultado. */
  cep: string;
  street: string | null;
  neighborhood: string | null;
  complement: string | null;
  city: string;
  state: string;
}
