import api from './api';
import { User, LoginData, RegisterData, AuthResponse } from '../types';

class AuthService {
    private tokenKey = 'token';

    async login(data: LoginData): Promise<AuthResponse> {
        const response = await api.post<AuthResponse>('/auth/token', {
            username: data.email,
            password: data.password
        });
        const { access_token, user } = response.data;
        this.setToken(access_token);
        return { access_token, user };
    }

    async register(data: RegisterData): Promise<AuthResponse> {
        const response = await api.post<AuthResponse>('/auth/register', {
            email: data.email,
            password: data.password
        });
        const { access_token, user } = response.data;
        this.setToken(access_token);
        return { access_token, user };
    }

    async logout(): Promise<void> {
        this.removeToken();
    }

    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>('/users/me');
        return response.data;
    }

    getToken(): string | null {
        return localStorage.getItem(this.tokenKey);
    }

    setToken(token: string): void {
        localStorage.setItem(this.tokenKey, token);
    }

    removeToken(): void {
        localStorage.removeItem(this.tokenKey);
    }

    isAuthenticated(): boolean {
        return !!this.getToken();
    }
}

export const authService = new AuthService();
