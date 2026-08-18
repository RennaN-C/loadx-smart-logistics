import type { ReactNode } from "react";

/**
 * Ícones desenhados aqui, não importados de biblioteca. São poucos e cada um
 * pesa algumas centenas de bytes; trazer um pacote inteiro só por causa de
 * desenho não se paga — foi o mesmo raciocínio que tirou o drei do projeto.
 *
 * Todos partilham a grade de 24 e o traço de 1.75. É essa repetição que faz o
 * conjunto parecer uma família só, em vez de figurinhas avulsas.
 *
 * São SEMPRE decorativos (`aria-hidden`): em todo lugar onde aparecem há um
 * rótulo em texto junto. Ícone que carrega significado sozinho precisa de nome
 * acessível, e aí quem usa é que deve fornecer — não este componente.
 */
export type IconName =
  | "home"
  | "truck"
  | "package"
  | "users"
  | "orders"
  | "planning"
  | "logout"
  | "plus"
  | "edit"
  | "calendar"
  | "priority";

const PATHS: Record<IconName, ReactNode> = {
  home: (
    <>
      <path d="M3.5 10.8 12 3.5l8.5 7.3" />
      <path d="M5.8 9.5V20.5h12.4V9.5" />
      <path d="M9.7 20.5v-5.6h4.6v5.6" />
    </>
  ),
  truck: (
    <>
      <rect x="2.5" y="6.5" width="11.5" height="9.5" rx="1" />
      <path d="M14 10.5h3.2l3.3 3.4V16H14z" />
      <circle cx="7" cy="18.5" r="2.2" />
      <circle cx="17.5" cy="18.5" r="2.2" />
    </>
  ),
  package: (
    <>
      <path d="M12 2.8l8.4 4.4v9.6L12 21.2l-8.4-4.4V7.2z" />
      <path d="M3.6 7.2 12 11.6l8.4-4.4" />
      <path d="M12 11.6v9.6" />
    </>
  ),
  users: (
    <>
      <circle cx="9.2" cy="8.4" r="3.4" />
      <path d="M3 20c0-3.4 2.8-5.6 6.2-5.6S15.4 16.6 15.4 20" />
      <path d="M16.2 5.4a3.4 3.4 0 0 1 0 6" />
      <path d="M17.6 14.8c2.2.7 3.4 2.5 3.4 5.2" />
    </>
  ),
  orders: (
    <>
      <rect x="4.5" y="4.5" width="15" height="16" rx="2" />
      <rect x="9" y="2.6" width="6" height="3.8" rx="1.2" />
      <path d="M8.6 11.5h6.8" />
      <path d="M8.6 15.5h4.6" />
    </>
  ),
  planning: (
    <>
      <path d="M12 2.6l9 4.9-9 4.9-9-4.9z" />
      <path d="M3 12.4l9 4.9 9-4.9" />
      <path d="M3 16.6l9 4.9 9-4.9" />
    </>
  ),
  logout: (
    <>
      <path d="M9.6 4.5H6a2.2 2.2 0 0 0-2.2 2.2v10.6A2.2 2.2 0 0 0 6 19.5h3.6" />
      <path d="M15.4 8.2 19.6 12l-4.2 3.8" />
      <path d="M19.6 12H9.4" />
    </>
  ),
  plus: (
    <>
      <path d="M12 5.2v13.6" />
      <path d="M5.2 12h13.6" />
    </>
  ),
  edit: <path d="M16.8 3.6a2.1 2.1 0 0 1 3 3L7.6 18.8l-4 1 1-4z" />,
  calendar: (
    <>
      <rect x="3.6" y="5.4" width="16.8" height="15" rx="2" />
      <path d="M3.6 10.2h16.8" />
      <path d="M8.2 3.2v4" />
      <path d="M15.8 3.2v4" />
    </>
  ),
  priority: (
    <>
      <path d="M5.6 21V3.6" />
      <path d="M5.6 4.4h12l-2.6 4.1 2.6 4.1h-12z" />
    </>
  ),
};

interface IconProps {
  readonly name: IconName;
  /** Em pixels. O traço não engorda junto, então ícone grande fica mais leve. */
  readonly size?: number;
}

export function Icon({ name, size = 18 }: IconProps) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/**
 * Marca da LoadX. Repete a linguagem do painel do login — eixos e volumes
 * apoiados na base —, para a barra lateral e a tela de entrada parecerem o
 * mesmo produto.
 */
export function BrandMark({ size = 26 }: { readonly size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 3.2v16.6h16.6" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" />
      <rect
        x="7"
        y="13.4"
        width="5.4"
        height="6.4"
        stroke="currentColor"
        strokeOpacity="0.5"
        strokeWidth="1.4"
      />
      <rect
        x="13.6"
        y="9"
        width="5.4"
        height="10.8"
        fill="var(--accent)"
        fillOpacity="0.2"
        stroke="var(--accent)"
        strokeWidth="1.4"
      />
    </svg>
  );
}
