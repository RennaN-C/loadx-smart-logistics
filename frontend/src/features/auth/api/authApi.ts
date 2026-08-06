import { api } from "../../../services/api";
import type { AuthenticatedUser, Role } from "../types";

interface LoginResponseDto {
  access_token: string;
  token_type: string;
}

interface UserDto {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
}

export interface LoginResult {
  accessToken: string;
  tokenType: string;
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const { data } = await api.post<LoginResponseDto>("/auth/login", { email, password });

  return {
    accessToken: data.access_token,
    tokenType: data.token_type,
  };
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

export async function getCurrentUser(): Promise<AuthenticatedUser> {
  const { data } = await api.get<UserDto>("/auth/me");

  return mapUserFromDto(data);
}
