import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { brandApi } from '@/apis/system_api'

export const useInfoStore = defineStore('info', () => {
  // 状态
  const infoConfig = ref({})
  const isLoading = ref(false)
  const isLoaded = ref(false)
  const debugMode = ref(false)

  // 计算属性 - 组织信息
  const organization = computed(() => infoConfig.value.organization || {
    name: "博古智问",
    logo: "/favicon.svg",
    avatar: "/avatar.jpg"
  })

  // 计算属性 - 品牌信息
  const branding = computed(() => infoConfig.value.branding || {
    name: "ZhiWen-Know",
    title: "ZhiWen-Know",
    subtitle: "大模型驱动的知识库管理工具",
    description: "结合知识库与知识图谱，提供更准确、更全面的回答"
  })

  // 计算属性 - 功能特性
  const features = computed(() => infoConfig.value.features || [
    "📚 灵活知识库",
    "🕸️ 知识图谱集成",
    "🤖 多模型切换",
    "🖼️ 多模态支持"
  ])

  // 计算属性 - 页脚信息
  const footer = computed(() => infoConfig.value.footer || {
    copyright: "© 博古智问 2025 [WIP] v0.12.138"
  })

  // 动作方法
  function setInfoConfig(newConfig) {
    infoConfig.value = newConfig
    isLoaded.value = true
  }

  function setDebugMode(enabled) {
    debugMode.value = enabled
  }

  function toggleDebugMode() {
    debugMode.value = !debugMode.value
  }

  async function loadInfoConfig(force = false) {
    // 如果已经加载过且不强制刷新，则不重新加载
    if (isLoaded.value && !force) {
      return infoConfig.value
    }

    try {
      isLoading.value = true
      const response = await brandApi.getInfoConfig()

      if (response.success && response.data) {
        setInfoConfig(response.data)
        console.debug('信息配置加载成功:', response.data)
        return response.data
      } else {
        console.warn('信息配置加载失败，使用默认配置')
        return null
      }
    } catch (error) {
      console.error('加载信息配置时发生错误:', error)
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function reloadInfoConfig() {
    try {
      isLoading.value = true
      const response = await brandApi.reloadInfoConfig()

      if (response.success && response.data) {
        setInfoConfig(response.data)
        console.debug('信息配置重新加载成功:', response.data)
        return response.data
      } else {
        console.warn('信息配置重新加载失败')
        return null
      }
    } catch (error) {
      console.error('重新加载信息配置时发生错误:', error)
      return null
    } finally {
      isLoading.value = false
    }
  }

    return {
    // 状态
    infoConfig,
    isLoading,
    isLoaded,
    debugMode,

    // 计算属性
    organization,
    branding,
    features,
    footer,

    // 方法
    setInfoConfig,
    setDebugMode,
    toggleDebugMode,
    loadInfoConfig,
    reloadInfoConfig
  }
})