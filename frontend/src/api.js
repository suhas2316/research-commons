const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000'

export async function apiRequest(path, options = {}) {
  const baseUrl = (API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')
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
