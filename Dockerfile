# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend + serve frontend
FROM python:3.11-slim
WORKDIR /app

COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./backend/static

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
