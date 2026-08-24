// Zephyr — shared types
// Mirrors the shapes returned by the FastAPI backend (routers/rules.py, routers/user.py).

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
export interface RuleDto {
  id: number;
  link: string;
  catchphrase: string;
  dm_message: string[];
  reply_message: string | null;
  is_active: boolean;
  count: number;
  created_at: string;
}

export interface RuleCreateRequest {
  link: string;
  catchphrase: string;
  dm_message: string[];
  reply_message: string | null;
}

export interface RuleUpdateRequest {
  link?: string;
  catchphrase?: string;
  dm_message?: string[];
  reply_message?: string | null;
  is_active?: boolean;
}

export interface JwtClaims {
  user_id?: string;
  type?: string;
  exp?: number;
}


