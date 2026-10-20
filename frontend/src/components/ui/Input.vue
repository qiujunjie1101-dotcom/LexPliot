<script setup lang="ts">
import { cn } from '@/lib/cn'

defineProps<{
  modelValue?: string
  type?: string
  placeholder?: string
  autocomplete?: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <input
    :value="modelValue"
    :type="type ?? 'text'"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :class="
      cn(
        'flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-slate-500 focus:ring-2 focus:ring-slate-200',
      )
    "
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  >
</template>
