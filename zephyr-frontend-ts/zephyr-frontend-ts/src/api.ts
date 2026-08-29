// Zephyr — API client
import { API_BASE_URL } from "./config.js";
import type {
  TokenResponse,
  RuleDto,
  RuleCreateRequest,
  RuleUpdateRequest,
  JwtClaims,
  UserProfile,
} from "./types.js";

const STORAGE_KEYS = {
  access: "zephyr_access_token",
  refresh: "zephyr_refresh_token",
} as const;

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}
export function getMe(): Promise<UserProfile> {
  return request<UserProfile>("/user/me");
}
function getAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.access);
}
function getRefreshToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.refresh);
}
function setTokens(t: Partial<TokenResponse>): void {
  if (t.access_token) localStorage.setItem(STORAGE_KEYS.access, t.access_token);
  if (t.refresh_token) localStorage.setItem(STORAGE_KEYS.refresh, t.refresh_token);
}
function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEYS.access);
  localStorage.removeItem(STORAGE_KEYS.refresh);
}
function isLoggedIn(): boolean {
  return !!getAccessToken();
}

function decodeToken(token: string): JwtClaims | null {
  try {
    const payload = token.split(".")[1];
    const json = decodeURIComponent(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json) as JwtClaims;
  } catch {
    return null;
  }
}

export const tokens = {
  get: getAccessToken,
  getRefresh: getRefreshToken,
  set: setTokens,
  clear: clearTokens,
  isLoggedIn,
  decodeToken,
};

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

let refreshInFlight: Promise<TokenResponse> | null = null;

async function refreshAccessToken(): Promise<TokenResponse> {
  const rt = getRefreshToken();
  if (!rt) throw new ApiError("Not signed in", 401);

  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE_URL}/user/refresh?refresh_token=${encodeURIComponent(rt)}`, {
      method: "POST",
    })
      .then(async (res) => {
        if (!res.ok) throw new ApiError("Session expired", res.status);
        const data = (await res.json()) as TokenResponse;
        setTokens(data);
        return data;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = opts;

  const doFetch = (): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) {
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && auth && getRefreshToken()) {
    try {
      await refreshAccessToken();
      res = await doFetch();
    } catch {
      clearTokens();
      throw new ApiError("Your session ended. Please sign in again.", 401);
    }
  }

  if (!res.ok) {
    let detail: string | null = null;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : null;
    } catch {
      /* no JSON body */
    }
    if (res.status === 401) clearTokens();
    throw new ApiError(detail ?? `Request failed (${res.status})`, res.status, detail);
  }

  if (res.status === 204) return null as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

export const loginUrl = (): string => `${API_BASE_URL}/user/login`;

export function exchangeCode(code: string): Promise<TokenResponse> {
  return request<TokenResponse>(`/user/instagram_callback?code=${encodeURIComponent(code)}`, {
    auth: false,
  });
}

export async function logout(): Promise<void> {
  const rt = getRefreshToken();
  try {
    if (rt) {
      await request(`/user/logout?refresh_token=${encodeURIComponent(rt)}`, { method: "POST" });
    }
  } catch {
    // best-effort
  } finally {
    clearTokens();
  }
}

export function deleteAccount(): Promise<void> {
  return request<void>("/user/me", { method: "DELETE" });
}

export function listRules(page = 1, limit = 10): Promise<RuleDto[]> {
  return request<RuleDto[]>(`/rules?page=${page}&limit=${limit}`);
}
export function getRule(id: number): Promise<RuleDto> {
  return request<RuleDto>(`/rules/${id}`);
}
export function createRule(payload: RuleCreateRequest): Promise<RuleDto> {
  return request<RuleDto>("/rules", { method: "POST", body: payload });
}
export function updateRule(id: number, payload: RuleUpdateRequest): Promise<RuleDto> {
  return request<RuleDto>(`/rules/${id}`, { method: "PATCH", body: payload });
}
export function deleteRule(id: number): Promise<void> {
  return request<void>(`/rules/${id}`, { method: "DELETE" });
}

export async function startCheckout(): Promise<string> {
  const res = await request<{ url: string }>("/payments/checkout");
  return res.url;
}

export async function hasActiveSubscription(): Promise<boolean> {
  try {
    await listRules(1, 1);
    return true;
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) return false;
    throw e;
  }
}
