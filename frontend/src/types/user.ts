export interface User {
    id: number;
    email: string;
    role: string;
    created_at: string;
    updated_at: string;
}

export interface LoginData {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
    password_confirmation: string;
}

export interface AuthResponse {
    user: User;
    access_token: string;
}
