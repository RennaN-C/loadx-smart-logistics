import { MfaRequired, type MfaChallenge } from "../mfaTypes";
import { api } from "../../../services/api";
import type { AuthenticatedUser, Role } from "../types";

export interface UserDto {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
  permissions?: string[];
  custom_profile_id?: string | null;
  custom_profile_name?: string | null;
}

export function mapUserFromDto(dto: UserDto): AuthenticatedUser {
  return {
    id: dto.id,
    name: dto.name,
    email: dto.email,
    role: dto.role,
    active: dto.active,
    createdAt: dto.created_at,
    ...(dto.permissions !== undefined ? { permissions: dto.permissions } : {}),
    ...(dto.custom_profile_id !== undefined ? { customProfileId: dto.custom_profile_id } : {}),
    ...(dto.custom_profile_name !== undefined ? { customProfileName: dto.custom_profile_name } : {}),
  };
}

export async function login(email: string, password: string): Promise<AuthenticatedUser> {
  const { data } = await api.post<UserDto | MfaChallenge>("/auth/login", { email, password });

  if ("challenge_token" in data) throw new MfaRequired(data);
  return mapUserFromDto(data);
}

export async function getCurrentUser(): Promise<AuthenticatedUser> {
  const { data } = await api.get<UserDto>("/auth/me");

  return mapUserFromDto(data);
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
