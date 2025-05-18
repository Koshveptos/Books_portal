import axios from 'axios';
import {
  Book,
  ApiResponse,
  BookRecommendation,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  User,
  Rating,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  AuthResponse,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  LoginData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  RegisterData,
  Author,
  Category,
  Tag,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  CreateBookData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  UpdateBookData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  CreateAuthorData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  UpdateAuthorData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  CreateCategoryData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  UpdateCategoryData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  CreateTagData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  UpdateTagData,
  Favorite,
  Like,
  Comment
} from '../types';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { authService } from './auth';

const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляем интерсептор для обработки ошибок
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
        }
        return Promise.reject(error);
    }
);

// Добавляем интерсептор для добавления токена
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Сервисы для книг
export const bookService = {
  getBooks: async (params?: {
    page?: number;
    limit?: number;
    sort?: string;
    category_id?: number;
    author_id?: number;
    search?: string;
  }): Promise<{ books: Book[]; total: number }> => {
    const response = await api.get('/books', { params });
    return response.data;
  },

  getBook: async (id: number): Promise<Book> => {
    const response = await api.get(`/books/${id}`);
    return response.data;
  },

  createBook: async (bookData: Partial<Book>): Promise<Book> => {
    const response = await api.post('/books', bookData);
    return response.data;
  },

  updateBook: async (id: number, bookData: Partial<Book>): Promise<Book> => {
    const response = await api.put(`/books/${id}`, bookData);
    return response.data;
  },

  deleteBook: async (id: number): Promise<void> => {
    await api.delete(`/books/${id}`);
  },

  getPopularBooks: async (limit: number = 10): Promise<Book[]> => {
    const response = await api.get('/books', {
      params: { sort: 'popular', limit }
    });
    return response.data.books;
  },

  getNewBooks: async (limit: number = 10): Promise<Book[]> => {
    const response = await api.get('/books', {
      params: { sort: 'new', limit }
    });
    return response.data.books;
  },

  getBooksByCategory: async (categoryId: number): Promise<{ books: Book[] }> => {
    const response = await api.get('/books', {
      params: { category_id: categoryId }
    });
    return response.data;
  },

  getBooksByAuthor: async (authorId: number): Promise<{ books: Book[] }> => {
    const response = await api.get('/books', {
      params: { author_id: authorId }
    });
    return response.data;
  },

  getBooksByTag: async (tagId: number): Promise<{ books: Book[] }> => {
    const response = await api.get('/books', {
      params: { tag_id: tagId }
    });
    return response.data;
  },

  searchBooks: async (query: string): Promise<{ books: Book[] }> => {
    const response = await api.get('/books', {
      params: { search: query }
    });
    return response.data;
  },

  rateBook: async (bookId: number, rating: number): Promise<Rating> => {
    const response = await api.post(`/books/${bookId}/rate`, { rating });
    return response.data;
  },

  addComment: async (bookId: number, content: string): Promise<Comment> => {
    const response = await api.post(`/books/${bookId}/comments`, { content });
    return response.data;
  },

  getComments: async (bookId: number): Promise<Comment[]> => {
    const response = await api.get(`/books/${bookId}/comments`);
    return response.data;
  },

  addToFavorites: async (bookId: number): Promise<void> => {
    await api.post(`/books/${bookId}/favorite`);
  },

  removeFromFavorites: async (bookId: number): Promise<void> => {
    await api.delete(`/books/${bookId}/favorite`);
  },

  likeBook: async (bookId: number): Promise<void> => {
    await api.post(`/books/${bookId}/like`);
  },

  unlikeBook: async (bookId: number): Promise<void> => {
    await api.delete(`/books/${bookId}/like`);
  }
};

// Сервисы для авторов
export const authorService = {
  getAuthors: async (): Promise<Author[]> => {
    const response = await api.get('/authors');
    return response.data;
  },

  getAuthor: async (id: number): Promise<Author> => {
    const response = await api.get(`/authors/${id}`);
    return response.data;
  },

  createAuthor: async (authorData: Partial<Author>): Promise<Author> => {
    const response = await api.post('/authors', authorData);
    return response.data;
  },

  updateAuthor: async (id: number, authorData: Partial<Author>): Promise<Author> => {
    const response = await api.put(`/authors/${id}`, authorData);
    return response.data;
  },

  deleteAuthor: async (id: number): Promise<void> => {
    await api.delete(`/authors/${id}`);
  }
};

// Сервисы для категорий
export const categoryService = {
  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/categories');
    return response.data;
  },

  getCategory: async (id: number): Promise<Category> => {
    const response = await api.get(`/categories/${id}`);
    return response.data;
  },

  createCategory: async (categoryData: Partial<Category>): Promise<Category> => {
    const response = await api.post('/categories', categoryData);
    return response.data;
  },

  updateCategory: async (id: number, categoryData: Partial<Category>): Promise<Category> => {
    const response = await api.put(`/categories/${id}`, categoryData);
    return response.data;
  },

  deleteCategory: async (id: number): Promise<void> => {
    await api.delete(`/categories/${id}`);
  }
};

// Сервисы для пользователя
export const userService = {
  getFavorites: async (): Promise<Favorite[]> => {
    const response = await api.get('/users/me/favorites');
    return response.data;
  },

  getRatings: async (): Promise<Rating[]> => {
    const response = await api.get('/users/me/ratings');
    return response.data;
  },

  getLikes: async (): Promise<Like[]> => {
    const response = await api.get('/users/me/likes');
    return response.data;
  }
};

// Сервисы для работы с тегами
export const tagService = {
  getTags: async (): Promise<Tag[]> => {
    const response = await api.get('/tags');
    return response.data;
  },

  getTag: async (id: number): Promise<Tag> => {
    const response = await api.get(`/tags/${id}`);
    return response.data;
  },

  createTag: async (tagData: Partial<Tag>): Promise<Tag> => {
    const response = await api.post('/tags', tagData);
    return response.data;
  },

  updateTag: async (id: number, tagData: Partial<Tag>): Promise<Tag> => {
    const response = await api.put(`/tags/${id}`, tagData);
    return response.data;
  },

  deleteTag: async (id: number): Promise<void> => {
    await api.delete(`/tags/${id}`);
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

// Публичные сервисы (не требуют авторизации)
export const publicService = {
  getBooks: async (): Promise<Book[]> => {
    const response = await api.get('/books');
    return response.data;
  },

  getBook: async (id: number): Promise<Book> => {
    const response = await api.get(`/books/${id}`);
    return response.data;
  },

  getAuthors: async (): Promise<Author[]> => {
    const response = await api.get('/authors');
    return response.data;
  },

  getAuthor: async (id: number): Promise<Author> => {
    const response = await api.get(`/authors/${id}`);
    return response.data;
  },

  getCategories: async (): Promise<Category[]> => {
    const response = await api.get('/categories');
    return response.data;
  },

  getCategory: async (id: number): Promise<Category> => {
    const response = await api.get(`/categories/${id}`);
    return response.data;
  },

  getBooksByAuthor: async (authorId: number): Promise<Book[]> => {
    const response = await api.get(`/authors/${authorId}/books`);
    return response.data;
  },

  getBooksByCategory: async (categoryId: number): Promise<Book[]> => {
    const response = await api.get(`/categories/${categoryId}/books`);
    return response.data;
  }
};

export default api;
