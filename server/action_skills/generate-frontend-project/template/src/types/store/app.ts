export type ThemeMode = 'light' | 'dark' | 'auto';

export interface AppState {
  themeMode: ThemeMode;
  sidebarOpened: boolean;
  sidebarCollapsed: boolean;
  cachedViews: string[];
  device: 'desktop' | 'mobile';
  language: string;
  size: 'large' | 'default' | 'small';
  loading: boolean;
  showBreadcrumb: boolean;
  showTabs: boolean;
  showFooter: boolean;
}

export interface AppActions {
  setThemeMode(mode: ThemeMode): void;
  toggleSidebar(): void;
  setSidebarOpened(opened: boolean): void;
  setSidebarCollapsed(collapsed: boolean): void;
  addCachedView(view: string): void;
  removeCachedView(view: string): void;
  clearCachedViews(): void;
  setDevice(device: 'desktop' | 'mobile'): void;
  setLanguage(language: string): void;
  setSize(size: 'large' | 'default' | 'small'): void;
  setLoading(loading: boolean): void;
  toggleShowBreadcrumb(): void;
  toggleShowTabs(): void;
  toggleShowFooter(): void;
}

export type AppStore = AppState & AppActions;
