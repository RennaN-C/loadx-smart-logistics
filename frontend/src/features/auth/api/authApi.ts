import { api } from "../../../services/api";
import type { AuthenticatedUser, Role } from "../types";

interface UserDto {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
}

export function mapUserFromDto(dto: UserDto): AuthenticatedUser {
  return {
    id: dto.id,
    name: dto.name,
    email: dto.email,
    role: dto.role,
    active: dto.active,
    createdAt: dto.created_at,
  };
}

export async function login(email: string, password: string): Promise<AuthenticatedUser> {
  const { data } = await api.post<UserDto>("/auth/login", { email, password });

  return mapUserFromDto(data);
}

export async function getCurrentUser(): Promise<AuthenticatedUser> {
  const { data } = await api.get<UserDto>("/auth/me");

  return mapUserFromDto(data);
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
