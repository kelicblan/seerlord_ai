import {
  desensitize,
  type DesensitizationConfig,
  type DesensitizationType,
} from '@/utils/desensitization';

export interface UseDesensitizationReturn {
  phone: (value: string) => string;
  email: (value: string) => string;
  idCard: (value: string) => string;
  bankCard: (value: string) => string;
  name: (value: string) => string;
  address: (value: string, visibleLength?: number) => string;
  custom: (
    value: string,
    config: NonNullable<DesensitizationConfig['customPattern']>
  ) => string;
  desensitizeByType: (value: string, type: DesensitizationType) => string;
  createDesensitizer: (config: DesensitizationConfig) => (value: string) => string;
}

export const useDesensitization = (): UseDesensitizationReturn => {
  const phone = (value: string): string => {
    return desensitize(value, { type: 'phone' });
  };

  const email = (value: string): string => {
    return desensitize(value, { type: 'email' });
  };

  const idCard = (value: string): string => {
    return desensitize(value, { type: 'idCard' });
  };

  const bankCard = (value: string): string => {
    return desensitize(value, { type: 'bankCard' });
  };

  const name = (value: string): string => {
    return desensitize(value, { type: 'name' });
  };

  const address = (value: string): string => {
    return desensitize(value, { type: 'address' });
  };

  const custom = (
    value: string,
    config: NonNullable<DesensitizationConfig['customPattern']>
  ): string => {
    return desensitize(value, { type: 'custom', customPattern: config });
  };

  const desensitizeByType = (value: string, type: DesensitizationType): string => {
    return desensitize(value, { type });
  };

  const createDesensitizer = (config: DesensitizationConfig) => {
    return (value: string): string => {
      return desensitize(value, config);
    };
  };

  return {
    phone,
    email,
    idCard,
    bankCard,
    name,
    address,
    custom,
    desensitizeByType,
    createDesensitizer,
  };
};
