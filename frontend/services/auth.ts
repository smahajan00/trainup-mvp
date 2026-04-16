import { apiRequest } from "../lib/api";
import type {
  AuthResponse,
  CurrentUserResponse,
  LoginRequest,
  RegisterRequest
} from "../types/auth";

export function registerUser(payload: RegisterRequest) {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload)
  });
}

export function loginUser(payload: LoginRequest) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload)
  });
}

export function getCurrentUser() {
  return apiRequest<CurrentUserResponse>("/auth/me");
}
