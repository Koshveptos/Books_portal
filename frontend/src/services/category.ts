import api from './api';
import { Category } from '../types/category';

class CategoryService {
    async getCategories(): Promise<Category[]> {
        const response = await api.get('/categories');
        return response.data;
    }

    async getCategory(id: number): Promise<Category> {
        const response = await api.get(`/categories/${id}`);
        return response.data;
    }

    async createCategory(category: Partial<Category>): Promise<Category> {
        const response = await api.post('/categories', category);
        return response.data;
    }

    async updateCategory(id: number, category: Partial<Category>): Promise<Category> {
        const response = await api.put(`/categories/${id}`, category);
        return response.data;
    }

    async deleteCategory(id: number): Promise<void> {
        await api.delete(`/categories/${id}`);
    }
}

export const categoryService = new CategoryService();
