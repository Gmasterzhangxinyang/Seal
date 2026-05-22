const API_BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'include',
  })

  if (res.status === 401) {
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new ApiError('Not authenticated', 401)
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
    throw new ApiError(data.error || `HTTP ${res.status}`, res.status)
  }

  return res.json()
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

export async function apiDelete<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: 'DELETE' })
}
