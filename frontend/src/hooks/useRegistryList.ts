import { useCallback, useState } from "react";
import type { ListParams } from "../services/pagination";
import type { Page } from "../types/api";
import { useResourceList } from "./useResourceList";

export type ArchiveStatus = "active" | "archived" | "all";

/** OC105: archive filtering is server-side, before pagination. */
export function useRegistryList<T>(load: (params: ListParams) => Promise<Page<T>>) {
  const [archiveStatus, setStatus] = useState<ArchiveStatus>("active");
  const filteredLoad = useCallback((params: ListParams) => load({ ...params, archiveStatus }), [load, archiveStatus]);
  const result = useResourceList(filteredLoad);
  function setArchiveStatus(value: ArchiveStatus) {
    result.goToPage(1);
    setStatus(value);
  }
  return { ...result, archiveStatus, setArchiveStatus };
}
