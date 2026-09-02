// Minimal client-side token storage. For a take-home this keeps the JWT in
// localStorage; a production app would prefer httpOnly cookies to mitigate XSS.

const TOKEN_KEY = "lm_token";

export function saveToken(token: string): void {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}
