import type { AuthResponse, AuthUser, LoginRequest, RegisterRequest } from '../types/auth';

// Production builds always use the real API, even if this flag is accidentally set.
export const authMockEnabled = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_AUTH === 'true';
const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');
let mockUser: AuthUser | null = null;
const demoProfiles = new Map<string, AuthUser>();

async function request(path: string, body?: LoginRequest | RegisterRequest, method = 'POST'): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${base}/auth/${path}`, {
      method, credentials: 'include', signal: controller.signal,
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) {
      if (response.status === 401) throw new Error('Email or password was not accepted. Please try again.');
      if (response.status === 409) throw new Error('An account with this email already exists. Please log in.');
      if (response.status === 429) throw new Error('Too many attempts. Please wait and try again.');
      throw new Error('Authentication is unavailable. Please try again once the backend is connected.');
    }
    return response.status === 204 ? undefined : await response.json();
  } catch (error) {
    if (error instanceof TypeError) throw new Error('Cannot connect to authentication. The backend may not be available yet.');
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('Authentication timed out. Please try again.');
    throw error;
  } finally { clearTimeout(timeout); }
}

function validResponse(value: unknown): AuthResponse {
  const user = (value as AuthResponse | null)?.user;
  if (!user || typeof user.id !== 'string' || typeof user.email !== 'string' || typeof user.fullName !== 'string') {
    throw new Error('Authentication returned an unexpected response. Please contact the project team.');
  }
  return { user };
}

async function mockResponse(email: string, fullName?: string): Promise<AuthResponse> {
  await new Promise(resolve => setTimeout(resolve, 650));
  if (email.toLowerCase() === 'error@example.com') throw new Error('Development mock: simulated authentication error. Try another email.');
  // Profile-only memory. Any form-valid password is accepted; this is UI simulation.
  const key = email.trim().toLowerCase();
  const previous = demoProfiles.get(key);
  mockUser = { id: previous?.id ?? `demo-${demoProfiles.size + 1}`, fullName: fullName ?? previous?.fullName ?? 'Demo Field Officer', email: key };
  demoProfiles.set(key, { ...mockUser });
  return { user: { ...mockUser } };
}

export const authService = {
  async login(input: LoginRequest) { return authMockEnabled ? mockResponse(input.email) : validResponse(await request('login', input)); },
  async register(input: RegisterRequest) { return authMockEnabled ? mockResponse(input.email, input.fullName) : validResponse(await request('register', input)); },
  async me(): Promise<AuthResponse> {
    if (!authMockEnabled) return validResponse(await request('me', undefined, 'GET'));
    if (!mockUser) throw new Error('No development mock session.');
    return { user: { ...mockUser } };
  },
  async logout(): Promise<void> {
    if (authMockEnabled) { mockUser = null; return; }
    await request('logout');
  },
};
