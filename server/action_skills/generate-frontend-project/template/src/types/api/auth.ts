export interface AuthSession {
  token: string;
  userName: string;
  userId: number;
  roles: string[];
  permissions: string[];
}

export interface LoginPayload {
  account: string;
  password: string;
  captcha?: string;
  remember?: boolean;
}

export interface LoginResponse {
  code: number;
  message: string;
  data: AuthSession;
}
