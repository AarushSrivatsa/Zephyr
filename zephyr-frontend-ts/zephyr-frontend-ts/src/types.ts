// Zephyr — shared types

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
  reply_message: string[] | null;
  is_active: boolean;
  is_case_sensitive: boolean;
  count: number;
  created_at: string;
}

export interface RuleCreateRequest {
  link: string;
  catchphrase: string;
  dm_message: string[];
  reply_message: string[] | null;
  is_case_sensitive: boolean;
}

export interface RuleUpdateRequest {
  link?: string;
  catchphrase?: string;
  dm_message?: string[];
  reply_message?: string[] | null;
  is_active?: boolean;
  is_case_sensitive?: boolean;
}

export interface JwtClaims {
  user_id?: string;
  type?: string;
  exp?: number;
}

export interface UserProfile {
  user_id: string;
  username: string;
  profile_pic_url: string;
}