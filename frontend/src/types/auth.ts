// Proposed contract: confirm endpoint paths and payloads with Siyam.
export interface AuthUser { id: string; fullName: string; email: string }
export interface LoginRequest { email: string; password: string }
export interface RegisterRequest extends LoginRequest { fullName: string }
export interface AuthResponse { user: AuthUser }
export interface AuthErrorResponse { message: string }
