import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { openAssistant } from "../../assistant/assistantApi";
import { PlanAIExplanation } from "./PlanAIExplanation";

vi.mock("../../assistant/assistantApi", () => ({ openAssistant: vi.fn() }));
it("abre conversa contextual somente após ação explícita, sem recalcular", () => {
  render(<PlanAIExplanation planId="persisted-plan" />);
  expect(openAssistant).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Perguntar ao LoadX sobre esta carga" }));
  expect(openAssistant).toHaveBeenCalledWith({ planId: "persisted-plan" });
});
