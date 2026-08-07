import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { getCustomer, listCustomers } from "../api/customersApi";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

export function CustomerPanel() {
  const { user } = useAuth();
  const {
    status,
    items: customers,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
  } = useResourceList(listCustomers);
  const edit = useEditTarget<Customer>(getCustomer);
  const [search, setSearch] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || edit.target !== null;

  // Só nome e cidade: a listagem não traz documento nem endereço.
  const visibleCustomers = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (term === "") return customers;

    return customers.filter(
      (customer) =>
        customer.name.toLowerCase().includes(term) || customer.city.toLowerCase().includes(term),
    );
  }, [customers, search]);

  function closeForm() {
    setIsCreating(false);
    edit.close();
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <>
      <div className="entity-toolbar">
        <input
          type="search"
          aria-label="Buscar cliente por nome ou cidade"
          placeholder="Buscar por nome ou cidade"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            + Novo cliente
          </button>
        ) : null}
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {customers.length} de {total} clientes. A busca atua nesta página.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando clientes…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapCustomerErrorToMessage(error)}</AlertBanner> : null}
      {edit.error ? <AlertBanner>{mapCustomerErrorToMessage(edit.error)}</AlertBanner> : null}

      {status === "success" && visibleCustomers.length === 0 ? (
        <p className="entity-state">
          {customers.length === 0
            ? "Nenhum cliente cadastrado ainda."
            : "Nenhum cliente encontrado com essa busca."}
        </p>
      ) : null}

      {visibleCustomers.length > 0 ? (
        <div className="entity-grid">
          {visibleCustomers.map((customer) => (
            <article key={customer.id} className="contact-card">
              <div className="contact-card-head">
                <p className="contact-card-name">{customer.name}</p>
              </div>
              <p className="contact-card-line">
                {customer.city} · {customer.state}
              </p>
              {canManage ? (
                <div className="contact-card-foot">
                  <button
                    type="button"
                    className="btn-link"
                    disabled={edit.loadingId === customer.id}
                    onClick={() => void edit.open(customer.id)}
                  >
                    {edit.loadingId === customer.id ? "Abrindo…" : "Editar"}
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="clientes" />
      ) : null}

      {isFormOpen ? (
        <Modal
          title={edit.target ? "Editar cliente" : "Novo cliente"}
          subtitle="Destino da entrega"
          onClose={closeForm}
        >
          <CustomerForm customer={edit.target ?? undefined} onSaved={handleSaved} onCancel={closeForm} />
        </Modal>
      ) : null}
    </>
  );
}
