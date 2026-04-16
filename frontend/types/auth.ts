export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
  created_at: string;
  has_profile: boolean;
};

export type RegisterRequest = {
  full_name: string;
  email: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

export type CurrentUserResponse = AuthUser;
