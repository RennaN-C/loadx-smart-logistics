import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, toSearchQuery, type PageDto, type SearchListParams } from "../../../services/pagination";
import { mapUserFromDto, type UserDto } from "../../auth/api/authApi";
import type { AuthenticatedUser, Role } from "../../auth/types";

export interface UserAccount extends AuthenticatedUser { driverId: string | null; driverName?: string | null }
interface AccountDto extends UserDto { driver_id: string | null; driver_name?: string | null }
export interface UserInput { name: string; email: string; role: Role; active: boolean; driverId: string | null; customProfileId?: string | null; password?: string }
export interface UserListParams extends SearchListParams { role?: Role; active?: boolean }
function mapAccount(dto: AccountDto): UserAccount { return { ...mapUserFromDto(dto), driverId: dto.driver_id, driverName: dto.driver_name ?? null }; }
function writeDto({ driverId, customProfileId, ...values }: Partial<UserInput>) { return { ...values, ...(driverId !== undefined ? { driver_id: driverId } : {}), ...(customProfileId !== undefined ? { custom_profile_id: customProfileId } : {}) }; }
export async function listUsers(params: UserListParams = {}) {
  const { data } = await api.get<PageDto<AccountDto>>("/users", { params: { ...toPageQuery(params), ...toSearchQuery(params), ...(params.role ? { role: params.role } : {}), ...(params.active !== undefined ? { active: params.active } : {}) } });
  return mapPageFromDto(data, mapAccount);
}
export async function getUser(id: string) { const { data } = await api.get<AccountDto>(`/users/${id}`); return mapAccount(data); }
export async function createUser(input: UserInput & { password: string }) { const { data } = await api.post<AccountDto>("/users", writeDto(input)); return mapAccount(data); }
export async function updateUser(id: string, input: Partial<UserInput>) { const { data } = await api.patch<AccountDto>(`/users/${id}`, writeDto(input)); return mapAccount(data); }
