import { create } from 'zustand'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { User } from '@/types/api'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,

  login: async (username: string, password: string) => {
    const data = await apiPost<User>('/auth/login', { username, password })
    set({ user: data, loading: false })
  },

  register: async (username: string, email: string, password: string) => {
    await apiPost('/auth/register', { username, email, password })
  },

  logout: async () => {
    await apiPost('/auth/logout')
    set({ user: null })
    window.location.href = '/login'
  },

  checkAuth: async () => {
    try {
      const data = await apiFetch<User>('/auth/me')
      set({ user: data, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },
}))
