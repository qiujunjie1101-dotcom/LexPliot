export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export type UserInfo = {
  id: string
  email: string
  display_name: string
}

export type TenantInfo = {
  id: string
  slug: string
  name: string
}

export type SessionResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
  tenant: TenantInfo
  roles: string[]
}

type ErrorBody = {
  error?: { code?: string; message?: string; details?: unknown }
  detail?: string | { message?: string }
}

export async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ErrorBody
    if (body.error?.message) return body.error.message
    if (typeof body.detail === 'string') return body.detail
    if (body.detail?.message) return body.detail.message
  } catch {
    // 非 JSON 错误响应，继续使用状态码兜底
  }
  return `请求失败（${response.status}）`
}
