import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  API_BASE,
  errorMessage,
  type SessionResponse,
  type TenantInfo,
  type UserInfo,
} from '@/lib/api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)
  const tenant = ref<TenantInfo | null>(null)
  const roles = ref<string[]>([])
  const loading = ref(false)
  let refreshPromise: Promise<boolean> | null = null

  const isAuthenticated = computed(() => accessToken.value !== null)

  function applySession(payload: SessionResponse) {
    accessToken.value = payload.access_token
    user.value = payload.user
    tenant.value = payload.tenant
    roles.value = payload.roles
  }

  function clearSession() {
    accessToken.value = null
    user.value = null
    tenant.value = null
    roles.value = []
  }

  async function readSession(response: Response): Promise<SessionResponse> {
    if (!response.ok) {
      throw new Error(await errorMessage(response))
    }
    return (await response.json()) as SessionResponse
  }

  async function login(email: string, password: string, tenantSlug?: string) {
    loading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          tenant_slug: tenantSlug || null,
        }),
      })
      applySession(await readSession(response))
    } finally {
      loading.value = false
    }
  }

  async function doRefresh(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!response.ok) {
        clearSession()
        return false
      }
      applySession((await response.json()) as SessionResponse)
      return true
    } catch {
      clearSession()
      return false
    }
  }

  async function refresh(): Promise<boolean> {
    if (refreshPromise) return refreshPromise
    refreshPromise = doRefresh()
    try {
      return await refreshPromise
    } finally {
      refreshPromise = null
    }
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } finally {
      clearSession()
    }
  }

  async function bootstrap(): Promise<boolean> {
    return accessToken.value !== null ? true : refresh()
  }

  return {
    accessToken,
    user,
    tenant,
    roles,
    loading,
    isAuthenticated,
    login,
    refresh,
    logout,
    bootstrap,
  }
})
