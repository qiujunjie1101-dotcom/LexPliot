import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from './auth'

const sessionPayload = {
  access_token: 'access-token-1',
  token_type: 'bearer',
  expires_in: 900,
  user: {
    id: 'user-1',
    email: 'admin@example.com',
    display_name: 'Admin',
  },
  tenant: {
    id: 'tenant-1',
    slug: 'acme',
    name: 'Acme',
  },
  roles: ['admin'],
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('logs in and stores the session in memory', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(sessionPayload))
    vi.stubGlobal('fetch', fetchMock)

    const auth = useAuthStore()
    await auth.login('admin@example.com', 'Admin123!', 'acme')

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.email).toBe('admin@example.com')
    expect(auth.tenant?.slug).toBe('acme')
    expect(auth.roles).toEqual(['admin'])
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('restores the session through refresh', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(sessionPayload)),
    )

    const auth = useAuthStore()
    expect(await auth.bootstrap()).toBe(true)
    expect(auth.accessToken).toBe('access-token-1')
  })

  it('clears the session on logout', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(sessionPayload))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    const auth = useAuthStore()
    await auth.refresh()
    expect(auth.isAuthenticated).toBe(true)

    await auth.logout()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
  })

  it('surfaces the backend error message on login failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'INVALID_CREDENTIALS', message: '邮箱或密码错误' } },
          401,
        ),
      ),
    )

    const auth = useAuthStore()
    await expect(
      auth.login('admin@example.com', 'wrong', 'acme'),
    ).rejects.toThrow('邮箱或密码错误')
  })
})
