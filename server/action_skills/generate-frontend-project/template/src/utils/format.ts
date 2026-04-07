export const formatDate = (date: Date | string | number, pattern: string = 'YYYY-MM-DD'): string => {
  const d = new Date(date);
  if (isNaN(d.getTime())) {
    return '';
  }

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');

  return pattern
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
};

export const formatNumber = (number: number | string, decimals: number = 0): string => {
  const num = typeof number === 'string' ? parseFloat(number) : number;
  if (isNaN(num)) {
    return '0';
  }
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const formatFileSize = (bytes: number | string): string => {
  const size = typeof bytes === 'string' ? parseInt(bytes, 10) : bytes;
  if (isNaN(size) || size < 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let unitIndex = 0;
  let fileSize = size;

  while (fileSize >= 1024 && unitIndex < units.length - 1) {
    fileSize /= 1024;
    unitIndex++;
  }

  return `${fileSize.toFixed(2)} ${units[unitIndex]}`;
};

export const formatCurrency = (amount: number | string, currency: string = 'CNY'): string => {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) {
    return '¥0.00';
  }

  const currencySymbols: Record<string, string> = {
    CNY: '¥',
    USD: '$',
    EUR: '€',
    GBP: '£',
    JPY: '¥',
  };

  const symbol = currencySymbols[currency] ?? currency + ' ';
  return `${symbol}${formatNumber(num, 2)}`;
};

export const formatPhone = (phone: string): string => {
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.length === 11) {
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7)}`;
  }
  if (cleaned.length === 10) {
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  return phone;
};

export const truncate = (text: string, maxLength: number, suffix: string = '...'): string => {
  if (!text || text.length <= maxLength) {
    return text;
  }
  return text.slice(0, maxLength - suffix.length) + suffix;
};
