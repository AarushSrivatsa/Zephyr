# ---- stage 1: compile the TS frontend ----
FROM node:20-alpine AS frontend-build
WORKDIR /frontend

COPY zephyr-frontend-ts/zephyr-frontend-ts/package.json zephyr-frontend-ts/zephyr-frontend-ts/package-lock.json* ./
RUN npm install

COPY zephyr-frontend-ts/zephyr-frontend-ts/ ./
RUN npm run build   # tsc: src/*.ts -> js/*.js

# ---- stage 2: python backend + built frontend ----
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# assemble the static frontend the backend will serve
RUN mkdir -p frontend/css frontend/js
COPY zephyr-frontend-ts/zephyr-frontend-ts/index.html frontend/
COPY zephyr-frontend-ts/zephyr-frontend-ts/dashboard.html frontend/
COPY zephyr-frontend-ts/zephyr-frontend-ts/login-callback.html frontend/
COPY zephyr-frontend-ts/zephyr-frontend-ts/css/ frontend/css/
COPY --from=frontend-build /frontend/js/ frontend/js/

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]