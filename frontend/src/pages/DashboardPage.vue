<script setup lang="ts">
import { useRouter } from 'vue-router'

import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const roleLabels: Record<string, string> = {
  admin: '管理员',
  legal_reviewer: '法务审查员',
  business_submitter: '业务提交者',
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <main class="mx-auto max-w-4xl p-8">
    <header class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          LexPilot 工作台
        </h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ auth.tenant?.name }} · {{ auth.user?.email }}
        </p>
      </div>
      <Button
        variant="outline"
        @click="logout"
      >
        退出登录
      </Button>
    </header>

    <div class="mt-8 grid gap-4 md:grid-cols-3">
      <Card>
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">
          当前租户
        </p>
        <p class="mt-2 text-lg font-medium">
          {{ auth.tenant?.slug }}
        </p>
        <p class="text-sm text-slate-500">
          {{ auth.tenant?.name }}
        </p>
      </Card>

      <Card>
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">
          当前用户
        </p>
        <p class="mt-2 text-lg font-medium">
          {{ auth.user?.display_name }}
        </p>
        <p class="text-sm text-slate-500">
          {{ auth.user?.email }}
        </p>
      </Card>

      <Card>
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">
          角色
        </p>
        <ul class="mt-2 flex flex-wrap gap-2">
          <li
            v-for="role in auth.roles"
            :key="role"
            class="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
          >
            {{ roleLabels[role] ?? role }}
          </li>
        </ul>
      </Card>
    </div>

    <Card class="mt-6">
      <h2 class="text-lg font-medium">
        Phase 0 已接通
      </h2>
      <p class="mt-2 text-sm leading-6 text-slate-600">
        认证、租户、角色与管理员用户管理已经可用。下一步将进入合同上传、文档解析与
        RAG 知识库。
      </p>
    </Card>
  </main>
</template>
