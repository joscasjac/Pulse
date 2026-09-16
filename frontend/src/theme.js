import { ref } from 'vue'

const KEY = 'pulse-theme'
export const theme = ref(localStorage.getItem(KEY) || 'light')

export function applyTheme() {
  document.documentElement.classList.toggle('dark', theme.value === 'dark')
}

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(KEY, theme.value)
  applyTheme()
}

applyTheme()
