export type DesensitizationType = 'phone' | 'idCard' | 'bankCard' | 'email' | 'name' | 'address';

export interface DesensitizationConfig {
  type: DesensitizationType | 'custom';
  visibleLength?: number;
  nameType?: 'full' | 'partial';
  customPattern?: RegExp;
}

export const desensitize = (value: string, config: DesensitizationConfig): string => {
  switch (config.type) {
    case 'phone':
      return desensitizePhone(value);
    case 'idCard':
      return desensitizeIdCard(value);
    case 'bankCard':
      return desensitizeBankCard(value);
    case 'email':
      return desensitizeEmail(value);
    case 'name':
      return desensitizeName(value, config.nameType);
    case 'address':
      return desensitizeAddress(value, config.visibleLength);
    case 'custom':
      if (config.customPattern) {
        return value.replace(config.customPattern, '*');
      }
      return value;
    default:
      return value;
  }
};

export const desensitizePhone = (phone: string): string => {
  if (!phone || phone.length < 11) {
    return phone;
  }
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
};

export const desensitizeIdCard = (idCard: string): string => {
  if (!idCard || idCard.length < 18) {
    return idCard;
  }
  return idCard.replace(/(\d{6})\d{8}(\d{4})/, '$1********$2');
};

export const desensitizeBankCard = (bankCard: string): string => {
  if (!bankCard) {
    return bankCard;
  }
  const cleaned = bankCard.replace(/\s/g, '');
  if (cleaned.length < 8) {
    return bankCard;
  }
  return cleaned.replace(/(\d{4})\d+(\d{4})/, '$1 **** **** $2');
};

export const desensitizeEmail = (email: string): string => {
  if (!email || !email.includes('@')) {
    return email;
  }
  const [username, domain] = email.split('@');
  if (username.length <= 2) {
    return `${username[0]}***@${domain}`;
  }
  return `${username.slice(0, 2)}***@${domain}`;
};

export const desensitizeName = (name: string, type: 'full' | 'partial' = 'partial'): string => {
  if (!name) {
    return name;
  }
  if (type === 'full') {
    return name.charAt(0) + '*'.repeat(name.length - 1);
  }
  if (name.length <= 1) {
    return '*';
  }
  if (name.length === 2) {
    return name.charAt(0) + '*';
  }
  return name.charAt(0) + '*'.repeat(name.length - 2) + name.charAt(name.length - 1);
};

export const desensitizeAddress = (address: string, visibleLength: number = 4): string => {
  if (!address) {
    return address;
  }
  if (address.length <= visibleLength) {
    return '*'.repeat(address.length);
  }
  return address.slice(0, visibleLength) + '*'.repeat(Math.min(address.length - visibleLength, 10));
};
