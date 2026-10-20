<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/cn'

const variants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-slate-900 text-white hover:bg-slate-700',
        outline: 'border border-slate-300 bg-white hover:bg-slate-100',
        ghost: 'hover:bg-slate-100',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

const props = defineProps<{
  variant?: VariantProps<typeof variants>['variant']
  size?: VariantProps<typeof variants>['size']
  type?: 'button' | 'submit' | 'reset'
}>()
</script>

<template>
  <button
    :type="props.type ?? 'button'"
    :class="cn(variants({ variant: props.variant, size: props.size }))"
  >
    <slot />
  </button>
</template>
