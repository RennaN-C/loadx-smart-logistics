import { useEffect, useRef, useState, type FormEvent } from "react";

import { isLoadingCode } from "./loadingErrorMessages";

export interface ScanOutcome {
  readonly ok: boolean;
  readonly message: string;
}

interface ScanFieldProps {
  readonly disabled: boolean;
  /** Texto explicando por que o campo está travado; some quando ele está livre. */
  readonly disabledReason?: string;
  readonly onScan: (code: string) => Promise<ScanOutcome>;
}

/**
 * Leitura de QR Code ou código de barras (OC75).
 *
 * Um leitor físico se comporta como teclado: digita o código inteiro muito
 * rápido e termina com Enter. Por isso aqui é um `<form>` com um campo de
 * texto, e não um componente de câmera — o mesmo campo serve para quem digita
 * à mão quando a etiqueta está danificada, que é o caminho manual que a OC75
 * manda preservar.
 *
 * O foco VOLTA para o campo depois de cada leitura. Sem isso o conferente
 * precisa clicar no campo entre um volume e outro, e com o leitor na mão isso
 * inviabiliza o uso.
 */
export function ScanField({ disabled, disabledReason, onScan }: ScanFieldProps) {
  const [code, setCode] = useState("");
  const [outcome, setOutcome] = useState<ScanOutcome | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const lido = code.trim();
    if (lido === "") return;

    // Recusa de formato ANTES da requisição. Não substitui a validação do
    // servidor — ele continua sendo a autoridade —, mas evita gastar uma ida ao
    // backend com algo que nem parece um código deste sistema, e responde na
    // hora, que é o que importa para quem está lendo volume atrás de volume.
    if (!isLoadingCode(lido)) {
      setOutcome({
        ok: false,
        message: "Código não reconhecido. Ele deve ser o código de um volume deste sistema.",
      });
      setCode("");
      inputRef.current?.focus();
      return;
    }

    setIsScanning(true);
    const resultado = await onScan(lido);
    setIsScanning(false);

    setOutcome(resultado);
    setCode("");
    inputRef.current?.focus();
  }

  return (
    <form className="scan-field" onSubmit={handleSubmit}>
      <label className="field-label" htmlFor="scan-code">
        LER CÓDIGO DO VOLUME
      </label>

      <div className="scan-field-row">
        <input
          id="scan-code"
          ref={inputRef}
          name="code"
          autoComplete="off"
          disabled={disabled || isScanning}
          placeholder="Aponte o leitor ou digite o código"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
        <button type="submit" className="btn-primary" disabled={disabled || isScanning || code.trim() === ""}>
          {isScanning ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Conferindo…</span>
            </>
          ) : (
            <span>Conferir código</span>
          )}
        </button>
      </div>

      {disabled && disabledReason ? <p className="entity-form-help">{disabledReason}</p> : null}

      {/* `aria-live` porque o resultado troca sem a tela mudar de lugar: quem
          usa leitor de tela não tem como perceber a troca sozinho. */}
      <p
        className={outcome?.ok === false ? "scan-result scan-result-bad" : "scan-result"}
        role="status"
        aria-live="polite"
      >
        {outcome?.message ?? ""}
      </p>
    </form>
  );
}
