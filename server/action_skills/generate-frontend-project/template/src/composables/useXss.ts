import {
  sanitizeHtml,
  escapeHtml,
  stripAllTags,
  stripDangerousAttrs,
  isSafeHtml,
  type XssOptions,
} from '@/utils/xss';

export interface UseXssReturn {
  sanitize: (html: string, options?: XssOptions) => string;
  escape: (str: string) => string;
  stripTags: (html: string) => string;
  stripTagsWithAllow: (html: string, allowSafeTags: string[]) => string;
  stripAttrs: (html: string) => string;
  checkSafe: (html: string) => boolean;
  createSanitizer: (options: XssOptions) => (html: string) => string;
}

export const useXss = (): UseXssReturn => {
  const sanitize = (html: string, options: XssOptions = {}): string => {
    return sanitizeHtml(html, options);
  };

  const escape = (str: string): string => {
    return escapeHtml(str);
  };

  const stripTags = (html: string): string => {
    return stripAllTags(html);
  };

  const stripTagsWithAllow = (html: string, allowSafeTags: string[]): string => {
    return sanitizeHtml(html, { allowedTags: allowSafeTags });
  };

  const stripAttrs = (html: string): string => {
    return stripDangerousAttrs(html);
  };

  const checkSafe = (html: string): boolean => {
    return isSafeHtml(html);
  };

  const createSanitizer = (options: XssOptions) => {
    return (html: string): string => {
      return sanitizeHtml(html, options);
    };
  };

  return {
    sanitize,
    escape,
    stripTags,
    stripTagsWithAllow,
    stripAttrs,
    checkSafe,
    createSanitizer,
  };
};
