const htmlEscapeMap: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;',
  '/': '&#x2F;',
  '`': '&#x60;',
  '=': '&#x3D;',
};

const unescapeMap: Record<string, string> = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#x27;': "'",
  '&#x2F;': '/',
  '&#x60;': '`',
  '&#x3D;': '=',
};

export interface XssOptions {
  stripTags?: boolean;
  allowedTags?: string | string[];
  allowedAttrs?: string[];
}

export const stripAllTags = (str: string): string => {
  return stripTags(str);
};

export const stripDangerousTags = (str: string): string => {
  const dangerousTags = ['script', 'style', 'iframe', 'object', 'embed', 'link', 'meta'];
  return stripTags(str, dangerousTags.join(','));
};

export const stripDangerousAttrs = (str: string): string => {
  const dangerousAttrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur'];
  let result = str;
  for (const attr of dangerousAttrs) {
    const pattern = new RegExp(`\\s*${attr}\\s*=\\s*["'][^"']*["']`, 'gi');
    result = result.replace(pattern, '');
  }
  return result;
};

export const isSafeHtml = (str: string): boolean => {
  if (!str) return true;
  const dangerousPatterns = [
    /<script[\s\S]*?<\/script>/gi,
    /javascript\s*:/gi,
    /on\w+\s*=/gi,
    /data\s*:\s*text\/html/gi,
  ];
  return !dangerousPatterns.some((pattern) => pattern.test(str));
};

export const escapeHtml = (str: string): string => {
  if (!str) return str;
  return str.replace(/[&<>"'`=/]/g, (char) => htmlEscapeMap[char] ?? char);
};

export const unescapeHtml = (str: string): string => {
  if (!str) return str;
  let result = str;
  for (const [escape, char] of Object.entries(unescapeMap)) {
    result = result.replace(new RegExp(escape, 'g'), char);
  }
  return result;
};

export const stripTags = (str: string, allowed?: string): string => {
  if (!str) return str;
  if (!allowed) {
    return str.replace(/<[^>]*>/g, '');
  }
  const allowedTags = allowed.split(',').map((tag) => tag.trim().toLowerCase());
  const allowedPattern = allowedTags.map((tag) => (tag.startsWith('<') ? tag.slice(1, -1) : tag)).join('|');
  const regex = new RegExp(`<(?!(${allowedPattern})\\s*\\/?)[^>]*>`, 'gi');
  return str.replace(regex, '');
};

export const xssFilter = (str: string, options?: {
  stripTags?: boolean;
  allowedTags?: string;
}): string => {
  if (!str) return str;

  let result = str;

  result = escapeHtml(result);

  if (options?.stripTags) {
    result = stripTags(result, options.allowedTags);
  }

  const dangerousPatterns = [
    /\s+on\w+\s*=/gi,
    /javascript\s*:/gi,
    /data\s*:\s*text\/html/gi,
    /vbscript\s*:/gi,
  ];

  for (const pattern of dangerousPatterns) {
    result = result.replace(pattern, '');
  }

  return result;
};

export const sanitizeHtml = (html: string, options?: XssOptions): string => {
  if (!html) return html;

  const allowedTags = options?.allowedTags ?? ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a'];
  const allowedAttrs = options?.allowedAttrs ?? ['href', 'title'];
  const tagsArray = Array.isArray(allowedTags) ? allowedTags : allowedTags.split(',').map(t => t.trim());

  let result = html;

  result = stripTags(result, tagsArray.join(','));

  const tagPattern = /<(\w+)([^>]*)>/gi;
  result = result.replace(tagPattern, (_match, tag, attrs) => {
    const lowerTag = tag.toLowerCase();
    if (!allowedTags.includes(lowerTag)) {
      return '';
    }

    if (!attrs.trim()) {
      return `<${lowerTag}>`;
    }

    const attrPattern = /(\w+)\s*=\s*["']([^"']*)["']/gi;
    const filteredAttrs: string[] = [];

    let attrMatch;
    while ((attrMatch = attrPattern.exec(attrs)) !== null) {
      const attrName = attrMatch[1].toLowerCase();
      if (allowedAttrs.includes(attrName)) {
        const attrValue = escapeHtml(attrMatch[2]);
        filteredAttrs.push(`${attrName}="${attrValue}"`);
      }
    }

    if (filteredAttrs.length > 0) {
      return `<${lowerTag} ${filteredAttrs.join(' ')}>`;
    }
    return `<${lowerTag}>`;
  });

  return result;
};
