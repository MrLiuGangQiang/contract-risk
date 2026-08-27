<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <!-- 合同文件轮廓 -->
    <path
      d="M13 5h16l8 8v27a3 3 0 0 1-3 3H13a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3Z"
      :stroke="color"
      stroke-width="2.4"
      stroke-linejoin="round"
    />
    <path d="M29 5v8h8" :stroke="color" stroke-width="2.4" stroke-linejoin="round" />
    <!-- 合同条款 -->
    <path d="M17 21h14" :stroke="color" stroke-width="2.4" stroke-linecap="round" />
    <path d="M17 27h14" :stroke="color" stroke-width="2.4" stroke-linecap="round" />
    <path d="M17 33h9" :stroke="color" stroke-width="2.4" stroke-linecap="round" />
    <!-- 安全盾（风险扫描护航） -->
    <path
      d="M33.5 26.5c3.8 1.4 5.7 3.8 5.7 6.6 0 3.8-2.9 6.6-5.7 8.4-2.8-1.8-5.7-4.6-5.7-8.4 0-2.8 1.9-5.2 5.7-6.6Z"
      :stroke="color"
      stroke-width="2.2"
      stroke-linejoin="round"
    />
    <path
      d="M32.6 34.9l2.1 2.1 3.4-3.6"
      :stroke="color"
      stroke-width="2.2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<script setup lang="ts">
/**
 * 合同图标（全局复用）：合同文件 + 安全盾校验，体现“合同风险扫描”主题。
 */
withDefaults(
  defineProps<{
    size?: number
    color?: string
  }>(),
  {
    size: 24,
    color: 'currentColor',
  },
)
</script>
