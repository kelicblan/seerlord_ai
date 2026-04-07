declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

import 'vue-router';
import 'pinia';

declare module 'vue-router' {
  interface RouteMeta {
    title?: string;
    icon?: string;
    requiresAuth?: boolean;
    guestOnly?: boolean;
    permissions?: string[];
    hidden?: boolean;
    keepAlive?: boolean;
  }
}

declare module 'pinia' {
  export interface Pinia {
    install(app: import('vue').App): void;
  }
}
