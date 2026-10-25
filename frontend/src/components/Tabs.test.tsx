import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Tabs } from "./Tabs";

function Example() {
  const [active, setActive] = useState("data");
  return <Tabs items={[{ id: "data", label: "Dados" }, { id: "security", label: "Segurança" }]} active={active} onChange={setActive} label="Perfil" />;
}

it("permite selecionar abas por setas, Home e End, mantendo foco e seleção juntos", () => {
  render(<Example />);
  const data = screen.getByRole("tab", { name: "Dados" });
  const security = screen.getByRole("tab", { name: "Segurança" });
  fireEvent.keyDown(data, { key: "ArrowRight" });
  expect(security).toHaveAttribute("aria-selected", "true");
  expect(security).toHaveFocus();
  fireEvent.keyDown(security, { key: "ArrowRight" });
  expect(data).toHaveFocus();
  fireEvent.keyDown(data, { key: "End" });
  expect(security).toHaveFocus();
  fireEvent.keyDown(security, { key: "Home" });
  expect(data).toHaveFocus();
  expect(data).toHaveAttribute("tabindex", "0");
  expect(security).toHaveAttribute("tabindex", "-1");
});
