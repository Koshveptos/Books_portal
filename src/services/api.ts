import axios from 'axios';
import { Book, ApiResponse, BookRecommendation, User, Rating, AuthResponse, LoginCredentials, RegisterData } from '../types';

// Создаем экземпляр axios с базовым URL и заголовками
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена авторизации
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Интерцептор для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { response } = error;

    // Обработка ошибок аутентификации
    if (response && response.status === 401) {
      // Если токен истек или недействителен, удаляем его и перезагружаем страницу
      if (localStorage.getItem('access_token')) {
        localStorage.removeItem('access_token');
        // Перенаправляем на страницу входа, если требуется
        // window.location.href = '/login';
      }
    }

    // Обработка ошибки сервера
    if (response && response.status === 500) {
      console.error('Ошибка сервера:', response.data);
    }

    // Обработка ошибки соединения
    if (!response) {
      console.error('Ошибка соединения с сервером');
    }

    return Promise.reject(error);
  }
);

// Сервисы для работы с книгами
export const bookService = {
  getBooks: async (): Promise<Book[]> => {
    // Публичный эндпоинт, можно обойтись без токена
    const response = await axios.get(`${api.defaults.baseURL}/books/books/`, {
      headers: {
        'Content-Type': 'application/json',
      }
    });
    return response.data;
  },

  getBook: async (id: number): Promise<Book> => {
    // Публичный эндпоинт, можно обойтись без токена
    const response = await axios.get(`${api.defaults.baseURL}/books/books/${id}`, {
      headers: {
        'Content-Type': 'application/json',
      }
    });
    return response.data;
  },

  searchBooks: async (query: string): Promise<Book[]> => {
    // Публичный эндпоинт, можно обойтись без токена
    const response = await axios.get(`${api.defaults.baseURL}/search/books?q=${query}`, {
      headers: {
        'Content-Type': 'application/json',
      }
    });
    return response.data.items;
  }
};

// Сервисы для работы с избранным
export const favoritesService = {
  getFavorites: async (): Promise<Book[]> => {
    const response = await api.get('/favorites/');
    return response.data;
  },

  addToFavorites: async (bookId: number): Promise<ApiResponse<null>> => {
    const response = await api.post(`/favorites/${bookId}`);
    return response.data;
  },

  removeFromFavorites: async (bookId: number): Promise<ApiResponse<null>> => {
    const response = await api.delete(`/favorites/${bookId}`);
    return response.data;
  }
};

// Сервисы для работы с лайками
export const likesService = {
  getLikedBooks: async (): Promise<Book[]> => {
    const response = await api.get('/likes/');
    return response.data;
  },

  likeBook: async (bookId: number): Promise<ApiResponse<null>> => {
    const response = await api.post(`/likes/${bookId}`);
    return response.data;
  },

  unlikeBook: async (bookId: number): Promise<ApiResponse<null>> => {
    const response = await api.delete(`/likes/${bookId}`);
    return response.data;
  }
};

// Сервисы для работы с рейтингами
export const ratingsService = {
  getUserRatings: async (): Promise<Rating[]> => {
    const response = await api.get('/ratings/');
    return response.data;
  },

  rateBook: async (bookId: number, rating: number, comment?: string): Promise<Rating> => {
    const response = await api.post(`/ratings/${bookId}`, { rating, comment });
    return response.data;
  },

  deleteRating: async (bookId: number): Promise<void> => {
    await api.delete(`/ratings/${bookId}`);
  }
};

// Сервисы для рекомендаций
export const recommendationService = {
  getRecommendations: async (type: string = 'hybrid'): Promise<BookRecommendation[]> => {
    const response = await api.get(`/recommendations/?recommendation_type=${type}`);
    return response.data;
  },

  getRecommendationsByAuthor: async (): Promise<BookRecommendation[]> => {
    const response = await api.get('/recommendations/by-author');
    return response.data;
  },

  getRecommendationsByCategory: async (): Promise<BookRecommendation[]> => {
    const response = await api.get('/recommendations/by-category');
    return response.data;
  },

  getRecommendationsByTag: async (): Promise<BookRecommendation[]> => {
    const response = await api.get('/recommendations/by-tag');
    return response.data;
  }
};

// Сервисы для аутентификации
export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post('/auth/jwt/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    // Сохраняем токен в localStorage
    localStorage.setItem('access_token', response.data.access_token);

    return response.data;
  },

  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  logout: (): void => {
    localStorage.removeItem('access_token');
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/users/me');
    return response.data;
  },

  getUserProfile: async (token?: string): Promise<User> => {
    const config = token ? { headers: { Authorization: `Bearer ${token}` } } : undefined;
    const response = await api.get('/users/me', config);
    return response.data;
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('access_token');
  }
};

export default api;
