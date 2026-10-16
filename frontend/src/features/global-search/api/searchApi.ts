import { api } from "../../../services/api";
export type SearchCategory = "order" | "customer" | "truck" | "driver" | "trip";
export interface SearchResult { category: SearchCategory; id: string; title: string; href: string }
export async function searchRecords(search: string, signal: AbortSignal): Promise<SearchResult[]> {
  const { data } = await api.get<{ results: SearchResult[] }>("/search", { params: { search, limit_per_category: 5 }, signal });
  return data.results;
}
