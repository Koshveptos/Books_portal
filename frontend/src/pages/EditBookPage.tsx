import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { Book, Author, Category, Tag } from '../types';

const EditBookPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [book, setBook] = useState<Book | null>(null);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bookRes, authorsRes, categoriesRes, tagsRes] = await Promise.all([
          api.get(`/books/${id}`),
          api.get('/authors'),
          api.get('/categories'),
          api.get('/tags')
        ]);

        setBook(bookRes.data);
        setAuthors(authorsRes.data);
        setCategories(categoriesRes.data);
        setTags(tagsRes.data);
      } catch (err) {
        setError('Ошибка при загрузке данных');
      }
    };

    fetchData();
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!book) return;

    setLoading(true);
    setError(null);

    try {
      const bookData = {
        ...book,
        authors: book.authors.map(author => author.id),
        categories: book.categories.map(category => category.id),
        tags: book.tags.map(tag => tag.id)
      };
      await api.put(`/books/${id}`, bookData);
      navigate(`/books/${id}`);
    } catch (err) {
      setError('Ошибка при обновлении книги');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setBook(prev => prev ? { ...prev, [name]: value } : null);
  };

  const handleMultiSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { name } = e.target;
    const selectedOptions = Array.from(e.target.selectedOptions, option => Number(option.value));

    if (name === 'authors') {
      const selectedAuthors = authors.filter(author => selectedOptions.includes(author.id));
      setBook(prev => prev ? { ...prev, authors: selectedAuthors } : null);
    } else if (name === 'categories') {
      const selectedCategories = categories.filter(category => selectedOptions.includes(category.id));
      setBook(prev => prev ? { ...prev, categories: selectedCategories } : null);
    } else if (name === 'tags') {
      const selectedTags = tags.filter(tag => selectedOptions.includes(tag.id));
      setBook(prev => prev ? { ...prev, tags: selectedTags } : null);
    }
  };

  if (!book) {
    return <div>Загрузка...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Редактировать книгу</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Название
              <input
                type="text"
                name="title"
                value={book.title}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Год издания
              <input
                type="number"
                name="year"
                value={book.year}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Издательство
              <input
                type="text"
                name="publisher"
                value={book.publisher}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              ISBN
              <input
                type="text"
                name="isbn"
                value={book.isbn}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Язык
              <input
                type="text"
                name="language"
                value={book.language}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Обложка (URL)
              <input
                type="url"
                name="cover"
                value={book.cover}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Файл (URL)
              <input
                type="url"
                name="file"
                value={book.file}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Авторы
              <select
                name="authors"
                multiple
                value={book.authors.map(author => author.id.toString())}
                onChange={handleMultiSelect}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              >
                {authors.map(author => (
                  <option key={author.id} value={author.id}>
                    {author.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Категории
              <select
                name="categories"
                multiple
                value={book.categories.map(category => category.id.toString())}
                onChange={handleMultiSelect}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              >
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name_categories}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Теги
              <select
                name="tags"
                multiple
                value={book.tags.map(tag => tag.id.toString())}
                onChange={handleMultiSelect}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              >
                {tags.map(tag => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="mt-6">
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Описание
            <textarea
              name="description"
              value={book.description}
              onChange={handleChange}
              rows={4}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              required
            />
          </label>
        </div>

        <div className="mt-6 flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate(`/books/${id}`)}
            className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditBookPage;
