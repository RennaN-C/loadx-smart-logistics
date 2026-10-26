import { useState } from "react";
import { api } from "../services/api";
import { ApiError } from "../types/api";
import { AlertBanner } from "./AlertBanner";

export function RecordLifecycleAction({ resource, id, active, onChanged }: {
  readonly resource: "customers" | "products" | "trucks" | "drivers";
  readonly id: string;
  readonly active: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function changeState() {
    setPending(true);
    setError(null);
    try {
      await api.patch(`/${resource}/${id}`, { active: !active });
      await onChanged();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Não foi possível alterar o cadastro.");
    } finally {
      setPending(false);
    }
  }
  return <div>
    <button type="button" className="btn-link" disabled={pending} onClick={() => void changeState()}>
      {pending ? "Salvando…" : active ? "Arquivar" : "Reativar"}
    </button>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
  </div>;
}
