export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/** Append query params, skipping empty values. */
export function withQuery(
  path: string,
  params: Record<string, string | undefined | null>,
): string {
  const usp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== '') usp.set(key, value)
  }
  const q = usp.toString()
  if (!q) return path
  return path.includes('?') ? `${path}&${q}` : `${path}?${q}`
}
