import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { User } from '../types';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string) => Promise<void>;
    logout: () => void;
    hasRole: (role: 'admin' | 'moderator' | 'user') => boolean;
    isAdmin: boolean;
    isModerator: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const token = localStorage.getItem('token');
                if (token) {
                    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                    const response = await api.get('/users/me');
                    setUser(response.data);
                }
            } catch (err) {
                console.error('Auth check error:', err);
                localStorage.removeItem('token');
                delete api.defaults.headers.common['Authorization'];
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();
    }, []);

    const login = async (email: string, password: string) => {
        try {
            setError(null);
            const response = await api.post('/auth/token', {
                username: email,
                password: password
            });
            const { access_token, user } = response.data;
            localStorage.setItem('token', access_token);
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            setUser(user);
            navigate('/');
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Ошибка при входе';
            setError(errorMessage);
            throw new Error(errorMessage);
        }
    };

    const register = async (email: string, password: string) => {
        try {
            setError(null);
            const response = await api.post('/auth/register', { email, password });
            const { access_token, user } = response.data;
            localStorage.setItem('token', access_token);
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            setUser(user);
            navigate('/');
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Ошибка при регистрации';
            setError(errorMessage);
            throw new Error(errorMessage);
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        delete api.defaults.headers.common['Authorization'];
        setUser(null);
        navigate('/');
    };

    const hasRole = (role: 'admin' | 'moderator' | 'user'): boolean => {
        if (!user) return false;
        return user.role === role;
    };

    const isAdmin = hasRole('admin');
    const isModerator = hasRole('moderator');

    const value = {
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        register,
        logout,
        hasRole,
        isAdmin,
        isModerator,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
