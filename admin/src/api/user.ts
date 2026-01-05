import api from './axios'

export const updatePassword = (data: any) => {
  return api.post('/api/v1/users/me/password', data)
}
