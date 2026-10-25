import { useUrlSearch } from "../../../hooks/useUrlSearch";
import { ImportAction } from "../../registration-imports/components/ImportAction";
import { useCallback, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { StatusPill } from "../../../components/StatusPill";
import { Modal } from "../../../components/Modal";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { Pagination } from "../../../components/Pagination";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useRegistryList } from "../../../hooks/useRegistryList";
import { ArchiveFilter } from "../../../components/ArchiveFilter";
import { RecordLifecycleAction } from "../../../components/RecordLifecycleAction";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics, hasPermission } from "../../auth/permissions";
import { getCustomer, listCustomers } from "../api/customersApi";
import { CustomerAddressPanel } from "./CustomerAddressPanel";
import type { CustomerListItem } from "../types";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";
import { Icon } from "../../../components/Icon";
import { RowActions } from "../../../components/RowActions";
import "../../../components/RegistryTable.css";

export function CustomerPanel() {
  const { user } = useAuth();
  const [search, setSearch] = useUrlSearch();
  const filteredLoad = useCallback((params: ListParams) => listCustomers({
    ...params,
    search,
  }), [search]);
  const {
    status,
    items: customers,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
    archiveStatus,
    setArchiveStatus,
  } = useRegistryList(filteredLoad);
  const edit = useEditTarget<Customer>(getCustomer);
  const [addressCustomer, setAddressCustomer] = useState<CustomerListItem | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user, "customers");
  const isFormOpen = isCreating || edit.target !== null;

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
      <div className="entity-toolbar contact-filterbar">
        <ImportAction enabled={hasPermission(user, "loadx.imports.manage")} entity="customers" onImported={refetch} />
        <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
        <input
          type="search"
          aria-label="Buscar cliente por nome ou cidade"
          placeholder="Buscar por nome ou cidade"
          value={search}
          onChange={(event) => { goToPage(1); setSearch(event.target.value); }}
          maxLength={MAX_SEARCH_LENGTH}
        />
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            <Icon name="plus" size={16} />
            Novo cliente
          </button>
        ) : null}
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {customers.length} de {total} clientes. Busca e filtros consideram toda a lista.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando clientes…</span>
        </p>
      ) : null}

      {status === "error" && error ? <><AlertBanner>{mapCustomerErrorToMessage(error)}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void refetch()}>Tentar novamente</button></> : null}
      {edit.error ? <AlertBanner>{mapCustomerErrorToMessage(edit.error)}</AlertBanner> : null}

      {status === "success" && customers.length === 0 ? (
        <p className="entity-state">
          {search.trim() === "" && archiveStatus === "active" && total === 0
            ? "Nenhum cliente cadastrado ainda."
            : "Nenhum cliente encontrado com essa busca."}
        </p>
      ) : null}

      {customers.length > 0 ? (
        <div className="registry-table-wrap"><table className="registry-table contact-table">
          <caption className="sr-only">Clientes cadastrados</caption>
          <thead><tr><th scope="col">Cliente</th><th scope="col">Cidade</th><th scope="col">Situação</th><th scope="col">Ações</th></tr></thead>
          <tbody>
          {customers.map((customer) => (
            <tr key={customer.id}>
              <td data-label="Cliente"><strong>{customer.name}</strong></td>
              <td data-label="Cidade">
                {customer.city} · {customer.state}
              </td>
              <td data-label="Situação"><StatusPill tone={customer.active ? "good" : "neutral"}>{customer.active ? "Ativo" : "Arquivado"}</StatusPill></td>
              <td data-label="Ações">
              {canManage ? (
                <RowActions label={`Ações de ${customer.name}`}>
                  <button type="button" className="btn-link" onClick={() => setAddressCustomer(customer)}>Endereços</button>
                  <RecordLifecycleAction resource="customers" id={customer.id} active={customer.active} onChanged={refetch} />
                  <button
                    type="button"
                    className="btn-link"
                    disabled={edit.loadingId === customer.id}
                    onClick={() => void edit.open(customer.id)}
                  >
                    {edit.loadingId === customer.id ? "Abrindo…" : "Editar"}
                  </button>
                </RowActions>
              ) : <span className="registry-no-action">Somente consulta</span>}
              </td>
            </tr>
          ))}
          </tbody></table></div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="clientes" />
      ) : null}

      {addressCustomer ? (
        <Modal title={`Endereços — ${addressCustomer.name}`} onClose={() => setAddressCustomer(null)}>
          <CustomerAddressPanel customerId={addressCustomer.id} onChanged={refetch} />
        </Modal>
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
