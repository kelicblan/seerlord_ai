import request from './axios'
import type { AxiosProgressEvent } from 'axios'

export interface UploadResponse {
  filename: string
  saved_filename: string
  file_path: string
}

export function uploadFile(formData: FormData, onUploadProgress?: (progressEvent: AxiosProgressEvent) => void) {
  return request<UploadResponse>({
    url: '/api/v1/files/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress
  })
}
