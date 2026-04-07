import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';
import { usePreferredDark } from '@vueuse/core';
import type { ThemeMode } from '../types';

export const useAppStore = defineStore(
  'app',
  () => {
    const themeMode = ref<ThemeMode>('system');
    const sidebarCollapsed = ref(false);
    const language = ref('zh-CN');
    const cachedViews = ref<string[]>([]);
    const device = ref<'desktop' | 'mobile'>('desktop');
    const size = ref<'large' | 'default' | 'small'>('default');
    const loading = ref(false);
    const showBreadcrumb = ref(true);
    const showTabs = ref(true);
    const showFooter = ref(true);

    const preferredDark = usePreferredDark();

    const resolvedTheme = computed<'light' | 'dark'>(() => {
      if (themeMode.value === 'system') {
        return preferredDark.value ? 'dark' : 'light';
      }
      return themeMode.value;
    });

    const isDark = computed(() => resolvedTheme.value === 'dark');
    const isMobile = computed(() => device.value === 'mobile');
    const isSidebarCollapsed = computed(() => sidebarCollapsed.value);

    const applyTheme = (theme: 'light' | 'dark') => {
      const rootElement = document.documentElement;
      rootElement.classList.toggle('dark', theme === 'dark');
      rootElement.dataset.theme = theme;
    };

    const initializeTheme = () => {
      applyTheme(resolvedTheme.value);
    };

    watch(resolvedTheme, applyTheme, { immediate: true });

    const setTheme = (mode: ThemeMode) => {
      themeMode.value = mode;
    };

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value;
    };

    const setSidebarCollapsed = (collapsed: boolean) => {
      sidebarCollapsed.value = collapsed;
    };

    const setLanguage = (lang: string) => {
      language.value = lang;
      document.documentElement.setAttribute('lang', lang);
    };

    const setDevice = (dev: 'desktop' | 'mobile') => {
      device.value = dev;
    };

    const setSize = (newSize: 'large' | 'default' | 'small') => {
      size.value = newSize;
    };

    const setLoading = (isLoading: boolean) => {
      loading.value = isLoading;
    };

    const addCachedView = (view: string) => {
      if (!cachedViews.value.includes(view)) {
        cachedViews.value.push(view);
      }
    };

    const removeCachedView = (view: string) => {
      const index = cachedViews.value.indexOf(view);
      if (index !== -1) {
        cachedViews.value.splice(index, 1);
      }
    };

    const clearCachedViews = () => {
      cachedViews.value = [];
    };

    const toggleShowBreadcrumb = () => {
      showBreadcrumb.value = !showBreadcrumb.value;
    };

    const toggleShowTabs = () => {
      showTabs.value = !showTabs.value;
    };

    const toggleShowFooter = () => {
      showFooter.value = !showFooter.value;
    };

    const resetSettings = () => {
      themeMode.value = 'system';
      sidebarCollapsed.value = false;
      language.value = 'zh-CN';
      cachedViews.value = [];
      device.value = 'desktop';
      size.value = 'default';
      showBreadcrumb.value = true;
      showTabs.value = true;
      showFooter.value = true;
    };

    const detectDevice = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setDevice('mobile');
        setSidebarCollapsed(true);
      } else {
        setDevice('desktop');
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('resize', detectDevice);
      detectDevice();
    }

    return {
      themeMode,
      sidebarCollapsed,
      language,
      cachedViews,
      device,
      size,
      loading,
      showBreadcrumb,
      showTabs,
      showFooter,
      resolvedTheme,
      isDark,
      isMobile,
      isSidebarCollapsed,
      setTheme,
      toggleSidebar,
      setSidebarCollapsed,
      setLanguage,
      setDevice,
      setSize,
      setLoading,
      addCachedView,
      removeCachedView,
      clearCachedViews,
      toggleShowBreadcrumb,
      toggleShowTabs,
      toggleShowFooter,
      initializeTheme,
      resetSettings,
    };
  },
  {
    persist: {
      key: 'app-preferences',
      pick: [
        'themeMode',
        'sidebarCollapsed',
        'language',
        'cachedViews',
        'device',
        'size',
        'showBreadcrumb',
        'showTabs',
        'showFooter',
      ],
    },
  },
);
