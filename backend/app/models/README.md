# Models Module

## Описание
Модуль содержит модели базы данных, определенные с использованием SQLAlchemy ORM.

## Модели

### book.py
Модели для работы с книгами и связанными сущностями:

#### Book
```python
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    publication_year = Column(Integer)
    language = Column(String)
    page_count = Column(Integer)
    rating = Column(Float, default=0.0)
    ratings_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    authors = relationship("Author", secondary=book_author, back_populates="books")
    categories = relationship("Category", secondary=book_category, back_populates="books")
    tags = relationship("Tag", secondary=book_tag, back_populates="books")
```

#### Author
```python
class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    biography = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    books = relationship("Book", secondary=book_author, back_populates="authors")
```

#### Category
```python
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name_categories = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    books = relationship("Book", secondary=book_category, back_populates="categories")
```

#### Tag
```python
class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name_tag = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    books = relationship("Book", secondary=book_tag, back_populates="tags")
```

### user.py
Модель пользователя:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    favorite_books = relationship("Book", secondary=favorites, back_populates="favorited_by")
    liked_books = relationship("Book", secondary=likes, back_populates="liked_by")
```

### rating.py
Модель рейтинга:

```python
class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    rating = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="ratings")
    book = relationship("Book", back_populates="ratings")
```

## Связи между таблицами

### book_author
```python
book_author = Table(
    "book_author",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id")),
    Column("author_id", Integer, ForeignKey("authors.id")),
)
```

### book_category
```python
book_category = Table(
    "book_category",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id")),
    Column("category_id", Integer, ForeignKey("categories.id")),
)
```

### book_tag
```python
book_tag = Table(
    "book_tag",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)
```

### favorites
```python
favorites = Table(
    "favorites",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("book_id", Integer, ForeignKey("books.id")),
)
```

### likes
```python
likes = Table(
    "likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("book_id", Integer, ForeignKey("books.id")),
)
```

## Использование

### Создание записи
```python
# Создание книги
book = Book(
    title="Название книги",
    description="Описание книги",
    publication_year=2023,
    language="ru",
    page_count=300
)

# Добавление авторов
book.authors = [author1, author2]

# Добавление категорий
book.categories = [category1, category2]

# Добавление тегов
book.tags = [tag1, tag2]

# Сохранение в базу данных
db.add(book)
await db.commit()
```

### Получение записей
```python
# Получение книги с авторами, категориями и тегами
book = await db.execute(
    select(Book)
    .options(
        selectinload(Book.authors),
        selectinload(Book.categories),
        selectinload(Book.tags)
    )
    .where(Book.id == book_id)
)
book = book.scalar_one_or_none()
```

### Обновление записи
```python
# Обновление книги
book.title = "Новое название"
book.description = "Новое описание"
await db.commit()
```

### Удаление записи
```python
# Удаление книги
await db.delete(book)
await db.commit()
```
