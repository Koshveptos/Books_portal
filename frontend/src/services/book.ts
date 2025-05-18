import api from './api';
import { Book, BookCreate, BookUpdate } from '../types/book';

export const bookService = {
    // Получить список книг
    async getBooks(params?: {
        skip?: number;
        limit?: number;
        category_id?: number;
        author_id?: number;
        tag_id?: number;
        search?: string;
    }): Promise<Book[]> {
        const response = await api.get('/books', { params });
        return response.data;
    },

    // Получить книгу по ID
    async getBook(id: number): Promise<Book> {
        const response = await api.get(`/books/${id}`);
        return response.data;
    },

    // Создать новую книгу
    async createBook(book: BookCreate): Promise<Book> {
        const response = await api.post('/books', book);
        return response.data;
    },

    // Обновить книгу
    async updateBook(id: number, book: BookUpdate): Promise<Book> {
        const response = await api.put(`/books/${id}`, book);
        return response.data;
    },

    // Удалить книгу
    async deleteBook(id: number): Promise<void> {
        await api.delete(`/books/${id}`);
    },

    // Получить книги по категории
    async getBooksByCategory(categoryId: number, skip = 0, limit = 10): Promise<Book[]> {
        const response = await api.get('/books', {
            params: { category_id: categoryId, skip, limit }
        });
        return response.data;
    },

    // Получить книги по автору
    async getBooksByAuthor(authorId: number, skip = 0, limit = 10): Promise<Book[]> {
        const response = await api.get('/books', {
            params: { author_id: authorId, skip, limit }
        });
        return response.data;
    },

    // Получить книги по тегу
    async getBooksByTag(tagId: number, skip = 0, limit = 10): Promise<Book[]> {
        const response = await api.get('/books', {
            params: { tag_id: tagId, skip, limit }
        });
        return response.data;
    },

    // Поиск книг
    async searchBooks(query: string, skip = 0, limit = 10): Promise<Book[]> {
        const response = await api.get('/books', {
            params: { search: query, skip, limit }
        });
        return response.data;
    }
};
