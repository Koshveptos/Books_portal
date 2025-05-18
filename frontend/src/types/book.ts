export interface Author {
    id: number;
    name: string;
    biography?: string;
    photo_url?: string;
}

export interface Category {
    id: number;
    name: string;
    description?: string;
}

export interface Tag {
    id: number;
    name: string;
}

export interface Book {
    id: number;
    title: string;
    description: string;
    author_id: number;
    category_id: number;
    publication_year: number;
    isbn: string;
    cover_image: string;
    rating: number;
    created_at: string;
    updated_at: string;
    author?: Author;
    category?: Category;
    tags?: Tag[];
}

export interface BookCreate {
    title: string;
    description: string;
    author_id: number;
    category_id: number;
    publication_year: number;
    isbn: string;
    cover_image?: string;
}

export interface BookUpdate {
    title?: string;
    description?: string;
    author_id?: number;
    category_id?: number;
    publication_year?: number;
    isbn?: string;
    cover_image?: string;
}
