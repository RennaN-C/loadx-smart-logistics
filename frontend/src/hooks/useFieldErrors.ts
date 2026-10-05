import { useCallback, useEffect, useRef, useState } from "react";

import { validationFieldMessages } from "../services/validationErrors";
import { ApiError } from "../types/api";

/** Função que confere UM campo e devolve a mensagem, ou `null` se está certo. */
export type FieldCheck = () => string | null;

/**
 * Erros por campo de um formulário: o que a tela detecta antes de enviar e o que
 * o backend devolve em 422, guardados no mesmo lugar.
 *
 * As chaves são os `id` dos controles (`customer-document`), não os nomes da
 * API. É o que deixa `fieldErrorProps(id, errors[id])` ser direto e o
 * `aria-describedby` apontar para o parágrafo certo.
 *
 * A validação só começa no primeiro envio. Validar enquanto se digita acusa
 * "CPF inválido" no terceiro dígito, quando a pessoa ainda está digitando —
 * depois do envio, aí sim o campo se corrige sozinho a cada tecla.
 */
export function useFieldErrors(apiFieldToControlId: Readonly<Record<string, string>>) {
  const formRef = useRef<HTMLFormElement>(null);
  const [errors, setErrors] = useState<Readonly<Record<string, string>>>({});
  const [hasSubmitted, setHasSubmitted] = useState(false);
  // Contador em vez de booleano: dois envios seguidos com o mesmo erro precisam
  // mandar o foco de volta, e um booleano que já é `true` não dispara efeito.
  const [focusRequest, setFocusRequest] = useState(0);

  useEffect(() => {
    if (focusRequest === 0) return;
    // Depois do render, senão `aria-invalid` ainda não existe no DOM.
    formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
  }, [focusRequest]);

  const apply = useCallback((found: Record<string, string>) => {
    setErrors(found);
    if (Object.keys(found).length > 0) setFocusRequest((current) => current + 1);
    return Object.keys(found).length === 0;
  }, []);

  /** Confere tudo no envio. `true` quando pode seguir. */
  const validateAll = useCallback(
    (checks: Readonly<Record<string, FieldCheck>>) => {
      setHasSubmitted(true);

      const found: Record<string, string> = {};
      for (const [controlId, check] of Object.entries(checks)) {
        const message = check();
        if (message !== null) found[controlId] = message;
      }

      return apply(found);
    },
    [apply],
  );

  /** Reconfere um campo enquanto se digita, só depois do primeiro envio. */
  const revalidate = useCallback(
    (controlId: string, check: FieldCheck) => {
      if (!hasSubmitted) return;

      setErrors((current) => {
        const message = check();
        if (message === null) {
          const semEste = { ...current };
          delete semEste[controlId];
          return semEste;
        }
        return { ...current, [controlId]: message };
      });
    },
    [hasSubmitted],
  );

  /**
   * Distribui um 422 pelos campos. `true` quando algum campo assumiu o erro —
   * aí a faixa de erro geral é dispensável e só repetiria a informação.
   */
  const applyApiError = useCallback(
    (error: ApiError) => {
      const byApiField = validationFieldMessages(error);

      const found: Record<string, string> = {};
      for (const [apiField, message] of Object.entries(byApiField)) {
        const controlId = apiFieldToControlId[apiField];
        if (controlId !== undefined) found[controlId] = message;
      }

      return !apply(found);
    },
    [apply, apiFieldToControlId],
  );

  /**
   * Converte uma falha de submissão na mensagem geral da tela.
   *
   * Quando o backend devolve erros de campo, eles já são distribuídos por
   * `applyApiError` e a faixa do topo fica vazia. Para qualquer outro erro, a
   * feature continua escolhendo a mensagem de domínio através de `fallback`.
   */
  const submissionErrorMessage = useCallback(
    (error: unknown, fallback: (apiError: ApiError) => string): string | null => {
      const apiError =
        error instanceof ApiError
          ? error
          : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");

      return applyApiError(apiError) ? null : fallback(apiError);
    },
    [applyApiError],
  );

  const clearAll = useCallback(() => {
    setErrors({});
  }, []);

  return {
    errors,
    formRef,
    validateAll,
    revalidate,
    applyApiError,
    submissionErrorMessage,
    clearAll,
  };
}
