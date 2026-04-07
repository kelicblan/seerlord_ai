export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PaginationParams {
  page: number;
  pageSize: number;
  total?: number;
}

export interface PaginatedResponse<T> {
  list: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

export interface ListParams {
  page?: number;
  pageSize?: number;
  keyword?: string;
  status?: number;
  startDate?: string;
  endDate?: string;
  orderBy?: string;
  orderType?: 'asc' | 'desc';
}

export interface SelectOption {
  label: string;
  value: string | number;
  disabled?: boolean;
}

export interface IdParam {
  id: number;
}

export interface IdsParam {
  ids: number[];
}

export interface StatusParam {
  id: number;
  status: number;
}

export interface BooleanParam {
  id: number;
  value: boolean;
}
