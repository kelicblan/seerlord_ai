import type { App, Directive } from 'vue';
import { vPermission } from './permission';
import { vCopy } from './copy';
import { vXss } from './xss';

export { vPermission, vCopy, vXss };

export interface DirectiveOptions {
  permission?: Directive;
  copy?: Directive;
  xss?: Directive;
}

export const directives: DirectiveOptions = {
  permission: vPermission,
  copy: vCopy,
  xss: vXss,
};

export default {
  install(app: App) {
    app.directive('permission', vPermission);
    app.directive('copy', vCopy);
    app.directive('xss', vXss);
  },
};
