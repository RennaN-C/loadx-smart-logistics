import { useCallback, useId, useRef, useState } from "react";

interface TooltipProps {
  /** O que a dica explica. Texto puro: a dica não recebe marcação. */
  readonly text: string;
  /** Nome acessível do gatilho, quando "Ajuda" não descrever bem o campo. */
  readonly label?: string;
}

/** Altura reservada para a bolha ao decidir se ela cabe acima do gatilho. */
const BUBBLE_ALLOWANCE = 120;

/**
 * Dica de contexto ao lado do rótulo.
 *
 * Abre no mouse E no teclado. Um `title` nativo não serve: ele não aparece para
 * quem navega por teclado, demora quase um segundo para surgir e não é
 * estilizável — e a dica aqui explica formato de campo, que é justamente o que
 * a pessoa precisa ler ANTES de digitar.
 *
 * O gatilho é um `<button>` de verdade, não um `<span>`, porque precisa receber
 * foco. `aria-describedby` liga a bolha ao gatilho, então o leitor de tela
 * anuncia a explicação junto do botão em vez de tratá-la como texto solto.
 *
 * A bolha abre para CIMA por padrão, para não tapar o campo que a pessoa vai
 * preencher, e vira para baixo quando não há espaço acima. Isso importa dentro
 * do modal: `.modal-overlay` usa `overflow: auto`, então uma bolha que subisse
 * além do topo seria recortada em vez de rolar.
 */
export function Tooltip({ text, label = "Ajuda" }: TooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [below, setBelow] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const bubbleId = useId();

  const open = useCallback(() => {
    const box = trigger.current?.getBoundingClientRect();
    setBelow(box !== undefined && box.top < BUBBLE_ALLOWANCE);
    setIsOpen(true);
  }, []);

  return (
    <span className="tooltip">
      <button
        ref={trigger}
        type="button"
        className="tooltip-trigger"
        aria-label={label}
        aria-describedby={isOpen ? bubbleId : undefined}
        aria-expanded={isOpen}
        onMouseEnter={open}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={open}
        onBlur={() => setIsOpen(false)}
        // Escape fecha sem tirar o foco do campo, como qualquer camada flutuante
        onKeyDown={(event) => {
          if (event.key === "Escape") setIsOpen(false);
        }}
      >
        i
      </button>
      {isOpen ? (
        <span
          className={below ? "tooltip-bubble tooltip-bubble-below" : "tooltip-bubble"}
          id={bubbleId}
          role="tooltip"
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}
