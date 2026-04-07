export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

export interface PaginationResponse<T> extends ApiResponse<T> {
  pagination: {
    page: number
    pageSize: number
    total: number
  }
}

export interface PaginationParams {
  page: number
  pageSize: number
  total?: number
}
