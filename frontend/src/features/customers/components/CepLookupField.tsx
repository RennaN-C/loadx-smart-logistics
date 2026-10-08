import { useRef, useState, type KeyboardEvent } from "react";

import { FormField } from "../../../components/FormField";
import { fieldErrorProps } from "../../../components/fieldErrorProps";
import { maskCep, onlyDigits } from "../../../components/masks";
import { ApiError } from "../../../types/api";
import { lookupAddressByCep } from "../api/customersApi";
import type { CepAddress } from "../types";
import { mapCepErrorToMessage } from "./customersErrorMessages";

const CEP_FIELD = "customer-cep";
const CEP_LENGTH = 8;

interface CepLookupFieldProps {
  /** Chamado só quando a consulta devolve endereço. Quem preenche é o formulário. */
  readonly initialCep?: string;
  readonly onCepChange?: (digits: string) => void;
  readonly onFound: (address: CepAddress) => void;
}

/**
 * Consulta de endereço por CEP (OC70).
 *
 * O cadastro legado de Customer usa somente o preenchimento. Endereços OC99
 * também recebem onCepChange para persistir o CEP normalizado.
 *
 * Nada aqui pode impedir o cadastro. Se a consulta falhar — CEP inexistente,
 * serviço fora do ar, tempo esgotado —, a mensagem aparece neste campo, os
 * dados já digitados ficam onde estão e o endereço continua podendo ser
 * preenchido à mão. É o que a OC62 pediu de quem consome.
 */
export function CepLookupField({ onFound, initialCep = "", onCepChange }: CepLookupFieldProps) {
  const [cep, setCep] = useState(maskCep(initialCep));
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [extra, setExtra] = useState<string | null>(null);
  /** Último CEP já consultado, para digitar e apagar não repetir a chamada. */
  const consultado = useRef("");
  /** Sequência da requisição: resposta atrasada de um CEP antigo é descartada. */
  const sequencia = useRef(0);

  async function consultar(digits: string) {
    const minha = sequencia.current + 1;
    sequencia.current = minha;

    setIsLoading(true);
    setErrorMessage(null);
    setExtra(null);

    try {
      const address = await lookupAddressByCep(digits);
      // Trocar o CEP rápido dispara duas consultas, e a primeira pode voltar
      // por último: sem isto, o endereço antigo sobrescreveria o novo.
      if (sequencia.current !== minha) return;

      setIsLoading(false);
      setExtra(describeExtra(address));
      onFound(address);
    } catch (error) {
      if (sequencia.current !== minha) return;

      setIsLoading(false);
      setErrorMessage(
        mapCepErrorToMessage(
          error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Erro inesperado."),
        ),
      );
    }
  }

  function handleChange(value: string) {
    const masked = maskCep(value);
    setCep(masked);

    const digits = onlyDigits(masked);
    onCepChange?.(digits);

    if (digits.length < CEP_LENGTH) {
      consultado.current = "";
      setErrorMessage(null);
      setExtra(null);
      return;
    }

    if (digits !== consultado.current) {
      consultado.current = digits;
      void consultar(digits);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;

    // Enter num campo de texto ENVIA o formulário. Aqui ele deve tentar o CEP de
    // novo, que é o que a pessoa espera depois de uma falha.
    event.preventDefault();
    const digits = onlyDigits(cep);
    if (digits.length === CEP_LENGTH && !isLoading) void consultar(digits);
  }

  const digits = onlyDigits(cep);

  return (
    <FormField
      id={CEP_FIELD}
      label="CEP (OPCIONAL)"
      tooltip="Preenche endereço, cidade e UF sozinho. O número e o complemento continuam seus. Se a consulta falhar, dá para preencher tudo à mão."
      error={errorMessage}
      hint={extra ?? undefined}
      narrow
    >
      <div className="cep-lookup">
        <input
          id={CEP_FIELD}
          name="cep"
          inputMode="numeric"
          maxLength={9}
          placeholder="01234-567"
          value={cep}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
          {...fieldErrorProps(CEP_FIELD, errorMessage)}
        />
        <button
          type="button"
          className="btn-secondary"
          disabled={digits.length !== CEP_LENGTH || isLoading}
          onClick={() => void consultar(digits)}
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Buscando…</span>
            </>
          ) : (
            <span>Buscar</span>
          )}
        </button>
      </div>
      {/* O preenchimento acontece em outros campos, longe daqui: sem anúncio,
          quem usa leitor de tela não fica sabendo que a tela mudou. */}
      <p className="sr-only" role="status">
        {isLoading ? "Consultando o CEP…" : ""}
      </p>
    </FormField>
  );
}

/**
 * Bairro e complemento viram DICA, não preenchimento.
 *
 * `Customer` não tem onde guardar os dois, e enfiá-los no endereço composto
 * exigiria um formato que ninguém aprovou. Jogar fora também seria errado: é
 * informação que a pessoa quer na hora de completar o endereço.
 */
function describeExtra(address: CepAddress): string | null {
  const partes = [
    address.neighborhood === null ? null : `Bairro: ${address.neighborhood}`,
    address.complement === null ? null : `Complemento: ${address.complement}`,
  ].filter((parte): parte is string => parte !== null);

  return partes.length === 0 ? null : partes.join(" · ");
}
