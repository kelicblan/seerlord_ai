import request from './axios'

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  created_at: string
  doc_count: number
}

export interface Document {
  id: string
  filename: string
  status: 'pending' | 'indexing' | 'completed' | 'failed'
  error_msg?: string
  chunk_count: number
  created_at: string
}

export interface DocumentEvent {
  id: string
  doc_id: string
  event_type: string
  message: string
  data?: Record<string, any> | null
  created_at: string
}

export interface DocumentChunk {
  point_id: string
  chunk_index: number
  text: string
  text_len: number
}

export interface DocumentChunkListResponse {
  items: DocumentChunk[]
}

export interface SearchResult {
  text: string
  score: number
  metadata: any
}

export function getKnowledgeBases() {
  return request<KnowledgeBase[]>({
    url: '/api/v1/knowledge/',
    method: 'get'
  })
}

export function createKnowledgeBase(data: { name: string; description?: string }) {
  return request<KnowledgeBase>({
    url: '/api/v1/knowledge/',
    method: 'post',
    data
  })
}

export function deleteKnowledgeBase(id: string) {
  return request({
    url: `/api/v1/knowledge/${id}`,
    method: 'delete'
  })
}

export function getDocuments(kbId: string) {
  return request<Document[]>({
    url: `/api/v1/knowledge/${kbId}/documents`,
    method: 'get'
  })
}

export function uploadDocument(kbId: string, formData: FormData) {
  return request({
    url: `/api/v1/knowledge/${kbId}/upload`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function deleteDocument(docId: string) {
  return request({
    url: `/api/v1/knowledge/documents/${docId}`,
    method: 'delete'
  })
}

export function retryDocument(docId: string) {
  return request({
    url: `/api/v1/knowledge/documents/${docId}/retry`,
    method: 'post'
  })
}

export function getDocumentEvents(docId: string) {
  return request<DocumentEvent[]>({
    url: `/api/v1/knowledge/documents/${docId}/events`,
    method: 'get'
  })
}

export function getDocument(docId: string) {
  return request<Document>({
    url: `/api/v1/knowledge/documents/${docId}`,
    method: 'get'
  })
}

export function getDocumentChunks(docId: string, limit: number = 5000) {
  return request<DocumentChunkListResponse>({
    url: `/api/v1/knowledge/documents/${docId}/chunks`,
    method: 'get',
    params: { limit }
  })
}

export function searchKnowledgeBase(kbId: string, query: string, top_k: number = 5) {
  return request<SearchResult[]>({
    url: `/api/v1/knowledge/${kbId}/search`,
    method: 'post',
    data: { query, top_k }
  })
}
