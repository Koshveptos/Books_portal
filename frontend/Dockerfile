FROM node:18-alpine

WORKDIR /app

# Установка зависимостей
COPY package*.json ./
RUN npm install

# Копирование файлов проекта
COPY . .

# Установка прав на директории
RUN chmod -R 755 /app

# Запуск приложения в режиме разработки
CMD ["npm", "start"]
