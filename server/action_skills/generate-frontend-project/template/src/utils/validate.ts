export const isEmail = (value: string): boolean => {
  if (!value) return false;
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(value.trim());
};

export const isPhone = (value: string): boolean => {
  if (!value) return false;
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(value.trim());
};

export const isIdCard = (value: string): boolean => {
  if (!value) return false;
  const idCardRegex = /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
  if (!idCardRegex.test(value.trim())) {
    return false;
  }

  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const checkCodes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];

  const id17 = value.trim().slice(0, 17);
  const sum = id17.split('').reduce((acc, char, index) => {
    return acc + parseInt(char, 10) * weights[index];
  }, 0);

  const checkCode = checkCodes[sum % 11];
  return value.trim().toUpperCase().endsWith(checkCode);
};

export const isUrl = (value: string): boolean => {
  if (!value) return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
};

export const isPassword = (value: string): { valid: boolean; message?: string } => {
  if (!value) {
    return { valid: false, message: '密码不能为空' };
  }
  if (value.length < 8) {
    return { valid: false, message: '密码长度不能少于8位' };
  }
  if (!/[a-zA-Z]/.test(value)) {
    return { valid: false, message: '密码必须包含字母' };
  }
  if (!/\d/.test(value)) {
    return { valid: false, message: '密码必须包含数字' };
  }
  return { valid: true };
};

export const isRequired = (value: unknown): boolean => {
  if (value === null || value === undefined) {
    return false;
  }
  if (typeof value === 'string') {
    return value.trim().length > 0;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return true;
};

export interface ValidationRule {
  field: string;
  label?: string;
  rules: Array<{
    validator: (value: unknown) => boolean | { valid: boolean; message?: string };
    message?: string;
  }>;
}

export interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

export const validateForm = (formData: Record<string, unknown>, rules: ValidationRule[]): ValidationResult => {
  const errors: Record<string, string> = {};
  let valid = true;

  for (const rule of rules) {
    const value = formData[rule.field];

    for (const r of rule.rules) {
      const result = r.validator(value);

      if (result === false || (typeof result === 'object' && !result.valid)) {
        const errorMessage = typeof result === 'object' && result.message
          ? result.message
          : r.message ?? `${rule.label ?? rule.field} 验证失败`;
        errors[rule.field] = errorMessage;
        valid = false;
        break;
      }
    }
  }

  return { valid, errors };
};
