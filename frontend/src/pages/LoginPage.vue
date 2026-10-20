<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('admin@example.com')
const password = ref('')
const tenantSlug = ref('acme')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value, tenantSlug.value)
    const redirect =
      typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败'
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-slate-100 p-6">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <h1 class="text-3xl font-semibold tracking-tight">
          LexPilot
        </h1>
        <p class="mt-1 text-sm text-slate-500">
          企业级合同审查 Agent
        </p>
      </div>

      <Card>
        <div class="mb-6">
          <h2 class="text-lg font-medium">
            登录
          </h2>
          <p class="mt-1 text-sm text-slate-500">
            选择租户并使用你的账号登录。
          </p>
        </div>

        <form
          class="space-y-4"
          @submit.prevent="submit"
        >
          <div class="space-y-2">
            <Label for="tenant">租户</Label>
            <Input
              id="tenant"
              v-model="tenantSlug"
              placeholder="acme"
              autocomplete="organization"
            />
          </div>

          <div class="space-y-2">
            <Label for="email">邮箱</Label>
            <Input
              id="email"
              v-model="email"
              type="email"
              placeholder="you@example.com"
              autocomplete="email"
            />
          </div>

          <div class="space-y-2">
            <Label for="password">密码</Label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>

          <p
            v-if="error"
            class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {{ error }}
          </p>

          <Button
            type="submit"
            class="w-full"
            :disabled="auth.loading"
          >
            {{ auth.loading ? '登录中…' : '登录' }}
          </Button>
        </form>
      </Card>

      <p class="mt-6 text-center text-xs text-slate-400">
        Phase 0 · 认证基础
      </p>
    </div>
  </main>
</template>
