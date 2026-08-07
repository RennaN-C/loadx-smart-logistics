import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../api/customersApi";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

export function CustomerPanel() {
  const { user } = useAuth();
  const { status, items: customers, error, refetch } = useResourceList(listCustomers);
  const [search, setSearch] = useState("");
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || editingCustomer !== null;

  const visibleCustomers = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (term === "") return customers;

    return customers.filter(
      (customer) =>
        customer.name.toLowerCase().includes(term) ||
        customer.document.toLowerCase().includes(term) ||
        customer.city.toLowerCase().includes(term),
    );
  }, [customers, search]);

  function closeForm() {
    setIsCreating(false);
    setEditingCustomer(null);
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
          aria-label="Buscar cliente por nome, documento ou cidade"
          placeholder="Buscar por nome, documento ou cidade"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            + Novo cliente
          </button>
        ) : null}
      </div>

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando clientes…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapCustomerErrorToMessage(error)}</AlertBanner> : null}

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
                <p className="entity-code">{customer.document}</p>
              </div>
              <p className="contact-card-line">{customer.address}</p>
              <p className="contact-card-line">
                {customer.city} · {customer.state}
              </p>
              {customer.phone ? <p className="contact-card-line">{customer.phone}</p> : null}
              {customer.notes ? <p className="contact-card-notes">{customer.notes}</p> : null}
              {canManage ? (
                <div className="contact-card-foot">
                  <button type="button" className="btn-link" onClick={() => setEditingCustomer(customer)}>
                    Editar
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {isFormOpen ? (
        <Modal
          title={editingCustomer ? "Editar cliente" : "Novo cliente"}
          subtitle="Destino da entrega"
          onClose={closeForm}
        >
          <CustomerForm
            customer={editingCustomer ?? undefined}
            onSaved={handleSaved}
            onCancel={closeForm}
          />
        </Modal>
      ) : null}
    </>
  );
}
