import api from './api';
import { Author } from '../types/author';

class AuthorService {
    async getAuthors(): Promise<Author[]> {
        const response = await api.get('/authors');
        return response.data;
    }

    async getAuthor(id: number): Promise<Author> {
        const response = await api.get(`/authors/${id}`);
        return response.data;
    }

    async createAuthor(author: Partial<Author>): Promise<Author> {
        const response = await api.post('/authors', author);
        return response.data;
    }

    async updateAuthor(id: number, author: Partial<Author>): Promise<Author> {
        const response = await api.put(`/authors/${id}`, author);
        return response.data;
    }

    async deleteAuthor(id: number): Promise<void> {
        await api.delete(`/authors/${id}`);
    }
}

export const authorService = new AuthorService();
