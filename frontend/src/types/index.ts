// Типы для книг
export interface Author {
  id: number;
  name: string;
  bio?: string;
  biography?: string;
  birth_date?: string;
  death_date?: string;
  photo: string;
  photo_url?: string;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name_categories: string;
  description?: string;
  image: string;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Book {
  id: number;
  title: string;
  description?: string;
  year?: number;
  cover_url?: string;
  cover?: string;
  isbn?: string;
  publisher?: string;
  language?: string;
  file?: string;
  authors: Author[];
  categories: Category[];
  tags: Tag[];
  average_rating?: number;
  ratings_count?: number;
  is_liked?: boolean;
  is_favorite?: boolean;
  created_at: string;
  updated_at: string;
}

// Типы для пользователей
export interface User {
  id: number;
  email: string;
  role: 'admin' | 'moderator' | 'user';
  created_at: string;
  updated_at: string;
}

// Типы для рейтингов и отзывов
export interface Rating {
  id: number;
  book_id: number;
  user_id: number;
  rating: number;
  comment?: string;
  created_at: string;
  book?: Book;
}

// Типы для рекомендаций
export interface BookRecommendation {
  book: Book;
  score: number;
  reason: string;
}

// Типы для ответов от API
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// Типы для аутентификации
export interface LoginData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user: User;
}

export interface RegisterData {
  email: string;
  password: string;
}

// Типы для создания и обновления сущностей
export interface CreateBookData {
  title: string;
  description?: string;
  year: number;
  publisher: string;
  isbn?: string;
  language: string;
  cover: string;
  file?: string;
  authors: number[];
  categories: number[];
  tags?: number[];
}

export interface UpdateBookData extends Partial<CreateBookData> {}

export interface CreateAuthorData {
  name: string;
  bio?: string;
  birth_date?: string;
  death_date?: string;
  photo: string;
}

export interface UpdateAuthorData extends Partial<CreateAuthorData> {}

export interface CreateCategoryData {
  name_categories: string;
  description?: string;
  image: string;
}

export interface UpdateCategoryData extends Partial<CreateCategoryData> {}

export interface CreateTagData {
  name: string;
}

export interface UpdateTagData extends Partial<CreateTagData> {}

// Типы для избранного и лайков
export interface Favorite {
  id: number;
  book_id: number;
  user_id: number;
  created_at: string;
}

export interface Like {
  id: number;
  book_id: number;
  user_id: number;
  created_at: string;
}

export interface Comment {
  id: number;
  book_id: number;
  user_id: number;
  content: string;
  created_at: string;
  updated_at: string;
  user: {
    id: number;
    email: string;
  };
}

export interface RatingProps {
  value: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
  className?: string;
}

export interface LikeButtonProps {
  isLiked: boolean;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export interface FavoriteButtonProps {
  isFavorite: boolean;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}
