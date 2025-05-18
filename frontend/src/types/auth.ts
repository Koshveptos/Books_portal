export interface User {
    id: number;
    email: string;
    username: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
    updated_at: string;
}

export interface LoginData {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    username: string;
    password: string;
    password_confirmation: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export {};
