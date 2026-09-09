import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Avatar } from "./Avatar";
import { initials } from "./initials";

describe("initials", () => {
  it("usa a primeira e a última palavra do nome composto", () => {
    expect(initials("Ana Maria Souza")).toBe("AS");
    expect(initials("Dev Frontend")).toBe("DF");
  });

  it("usa as duas primeiras letras quando só há uma palavra", () => {
    expect(initials("Aurora")).toBe("AU");
  });

  it("aguenta nome de uma letra só", () => {
    expect(initials("A")).toBe("A");
  });

  it("não quebra com espaço sobrando nem com nome vazio", () => {
    // a listagem resolve o nome do cliente por id; se o id não casar, sobra vazio
    expect(initials("  Distribuidora   Aurora  ")).toBe("DA");
    expect(initials("   ")).toBe("?");
    expect(initials("")).toBe("?");
  });

  it("mantém acento legível ao subir para maiúscula", () => {
    expect(initials("Ícaro Álvares")).toBe("ÍÁ");
  });
});

describe("Avatar", () => {
  it("é decorativo: o nome já está escrito ao lado dele", () => {
    const { container } = render(<Avatar name="Dev Frontend" />);

    expect(screen.queryByText("Dev Frontend")).not.toBeInTheDocument();
    expect(container.querySelector(".avatar")).toHaveAttribute("aria-hidden", "true");
  });

  it("acompanha o tamanho pedido, letra inclusive", () => {
    const { container } = render(<Avatar name="Ana Souza" size={50} />);
    const avatar = container.querySelector(".avatar");

    expect(avatar).toHaveStyle({ width: "50px", height: "50px", fontSize: "18px" });
  });
});
