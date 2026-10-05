import { useCallback, useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Icon, type IconName } from "../../../components/Icon";
import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import { ApiError } from "../../../types/api";
import { getOperationalIndicators } from "../api/operationalIndicatorsApi";
import type { OperationalIndicators } from "../types";
import "./OperationsDashboardPage.css";

/**
 * Como cada período da OC69 é dito em português.
 *
 * Fica num mapa, e não num `if`, porque o valor vem do contrato: período novo
 * que a tela não conheça aparece cru, em vez de ser traduzido por chute.
 */
const PERIOD_LABELS: Readonly<Record<string, string>> = {
  CURRENT_SNAPSHOT: "situação agora",
  ALL_TIME: "desde o início",
};

interface Numero {
  readonly label: string;
  readonly value: number;
  /** Explica o que o número conta, quando o rótulo sozinho não basta. */
  readonly note?: string;
  /** Destaca o que costuma exigir ação. */
  readonly alert?: boolean;
}

interface Grupo {
  readonly id: string;
  readonly title: string;
  readonly icon: IconName;
  readonly period: string;
  readonly numbers: readonly Numero[];
}

function montarGrupos(dados: OperationalIndicators): readonly Grupo[] {
  return [
    {
      id: "fleet",
      title: "Frota",
      icon: "truck",
      period: dados.fleet.period,
      numbers: [
        { label: "CAMINHÕES", value: dados.fleet.total },
        { label: "DISPONÍVEIS", value: dados.fleet.available, note: "Prontos para receber carga." },
        { label: "INDISPONÍVEIS", value: dados.fleet.unavailable },
        {
          label: "EM OPERAÇÃO",
          value: dados.fleet.withOperationConflict,
          note: "Já comprometidos com outra operação.",
        },
        { label: "ATIVOS", value: dados.fleet.active },
        { label: "INATIVOS", value: dados.fleet.inactive, note: "Fora da operação por cadastro." },
      ],
    },
    {
      id: "trips",
      title: "Viagens",
      icon: "planning",
      period: dados.trips.period,
      numbers: [
        { label: "TOTAL", value: dados.trips.total },
        { label: "PROGRAMADAS", value: dados.trips.scheduled },
        { label: "EM ROTA", value: dados.trips.inRoute },
        { label: "FINALIZADAS", value: dados.trips.finished },
      ],
    },
    {
      id: "deliveries",
      title: "Entregas",
      icon: "package",
      period: dados.deliveries.period,
      numbers: [
        { label: "TOTAL", value: dados.deliveries.total },
        { label: "PENDENTES", value: dados.deliveries.pending },
        { label: "EM ENTREGA", value: dados.deliveries.inDelivery },
        { label: "ENTREGUES", value: dados.deliveries.delivered },
      ],
    },
    {
      id: "occurrences",
      title: "Ocorrências",
      icon: "priority",
      period: dados.occurrences.period,
      numbers: [
        {
          label: "REGISTRADAS",
          value: dados.occurrences.total,
          note: "Problemas relatados durante entregas.",
          alert: dados.occurrences.total > 0,
        },
      ],
    },
  ];
}

/**
 * Painel operacional (OC74).
 *
 * Todo número vem de `GET /operational-indicators`. **Nada é calculado aqui** —
 * nem somas, nem porcentagens, nem médias. A OC69 deixou taxas e percentuais de
 * fora por não haver contrato de dados uniforme para eles, e derivá-los na tela
 * seria inventar métrica sem suporte, que é o que a OC74 põe fora de escopo.
 *
 * Fica separado de `/reports` de propósito. Aquela tela apura PEDIDOS somando no
 * cliente e avisa o limite de 1000; esta só exibe o que o servidor apurou. São
 * dois contratos de confiança diferentes, e juntá-los numa aba só borraria
 * justamente a distinção que a OC74 cobra.
 */
export function OperationsDashboardPage() {
  const [dados, setDados] = useState<OperationalIndicators | null>(null);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setStatus("loading");
    setErrorMessage(null);

    try {
      setDados(await getOperationalIndicators());
      setStatus("success");
    } catch (error) {
      const apiError =
        error instanceof ApiError
          ? error
          : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(fallbackErrorMessage(apiError));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Painel operacional</h1>
          <p className="entity-lede">
            Números apurados pelo servidor. Nenhum é calculado nesta tela.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          disabled={status === "loading"}
          onClick={() => void carregar()}
        >
          {status === "loading" ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Atualizando…</span>
            </>
          ) : (
            <span>Atualizar</span>
          )}
        </button>
      </header>

      {status === "loading" && dados === null ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando indicadores…</span>
        </p>
      ) : null}

      {status === "error" ? (
        <>
          <AlertBanner>{errorMessage}</AlertBanner>
          <button type="button" className="btn-secondary" onClick={() => void carregar()}>
            Tentar novamente
          </button>
        </>
      ) : null}

      {dados !== null && status !== "error"
        ? montarGrupos(dados).map((grupo) => <GrupoDeIndicadores key={grupo.id} grupo={grupo} />)
        : null}
    </div>
  );
}

function GrupoDeIndicadores({ grupo }: { readonly grupo: Grupo }) {
  return (
    <section className="ops-block" aria-labelledby={`ops-${grupo.id}`}>
      <div className="ops-block-head">
        <h2 id={`ops-${grupo.id}`}>
          <Icon name={grupo.icon} size={17} />
          {grupo.title}
        </h2>
        {/* O período é parte do significado do número, não enfeite: "2 em rota"
            sem dizer de quando não quer dizer nada. */}
        <p>{PERIOD_LABELS[grupo.period] ?? grupo.period}</p>
      </div>

      <div className="ops-grid">
        {grupo.numbers.map((numero) => (
          <div
            key={numero.label}
            className={numero.alert ? "ops-kpi ops-kpi-alert" : "ops-kpi"}
          >
            <span className="ops-kpi-label">{numero.label}</span>
            <span className="ops-kpi-value">{numero.value}</span>
            {numero.note === undefined ? null : (
              <span className="ops-kpi-note">{numero.note}</span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
