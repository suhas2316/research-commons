const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim()

export async function apiRequest(path, options = {}) {
  if (!API_BASE_URL) {
    throw new Error('Backend URL is not configured. Set VITE_API_BASE_URL in frontend/.env.')
  }

  const baseUrl = API_BASE_URL.replace(/\/+$/, '')
  const normalizedPath = path.replace(/^\/+/, '')
  const response = await fetch(new URL(normalizedPath, `${baseUrl}/`), {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  const payload = response.status === 204 ? null : await response.json()
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string'
      ? payload.detail
      : Array.isArray(payload?.detail)
        ? payload.detail.map((item) => item.msg).filter(Boolean).join('; ')
        : ''
    throw new Error(detail || `API request failed (${response.status}): ${response.statusText}`)
  }

  return payload
}
