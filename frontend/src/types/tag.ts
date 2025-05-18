export interface Tag {
  id: number;
  name_tag: string;
  books_count?: number;
}

export interface TagWithBooks extends Tag {
  books: Book[];
}

export interface Book {
  id: number;
  title: string;
  description: string;
  publication_year: number;
  language: string;
  page_count: number;
  rating: number;
  ratings_count: number;
  authors: Author[];
  categories: Category[];
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface Author {
  id: number;
  name: string;
  biography?: string;
  photo?: string;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name_categories: string;
}
