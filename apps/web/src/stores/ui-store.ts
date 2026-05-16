import { create } from 'zustand'
import i18n from '@/i18n'

interface UIState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  locale: 'zh' | 'en'
  setLocale: (locale: 'zh' | 'en') => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  locale: (localStorage.getItem('mec202-lang') as 'zh' | 'en') || 'zh',
  setLocale: (locale) => {
    i18n.changeLanguage(locale)
    localStorage.setItem('mec202-lang', locale)
    set({ locale })
    document.documentElement.lang = locale
  },
}))
