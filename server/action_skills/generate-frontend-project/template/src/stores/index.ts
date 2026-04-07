import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

export const pinia = createPinia();

pinia.use(piniaPluginPersistedstate);

export { useAppStore } from './modules/app';
export { useAuthStore } from './modules/auth';
export { useUserStore } from './modules/user';
export { useOfflineStore } from './modules/offline';

export * from './types';
