<template>
  <!-- 钉钉官方 Logo：使用真实应用图标（来源：钉钉官网公开品牌图） -->
  <img
    class="dingtalk-logo"
    src="/dingtalk-logo.png"
    alt="钉钉"
    :width="size"
    :height="size"
  />
</template>

<script setup lang="ts">
/** 钉钉图标（全局复用）：默认 20px，可按需传 size 放大。 */
withDefaults(defineProps<{ size?: number }>(), { size: 20 })
</script>
