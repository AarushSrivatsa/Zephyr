# ---- stage 1: compile the TS frontend + Tailwind CSS ----
FROM node:20-alpine AS frontend-build
WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build   # tsc: ts/*.ts -> js/*.js, tailwindcss: css/input.css -> css/tailwind.css

# ---- stage 2: python backend + built frontend ----
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# assemble the static frontend the backend will serve (flat — main.py maps
# each clean URL to a specific file in this directory by name)
RUN mkdir -p static/css static/js static/assets
COPY frontend/html/index.html static/
COPY frontend/html/dashboard.html static/
COPY frontend/html/login-callback.html static/
COPY frontend/html/privacy-policy.html static/
COPY frontend/html/data-deletion.html static/
COPY frontend/assets/ static/assets/
COPY --from=frontend-build /frontend/css/tailwind.css static/css/tailwind.css
COPY --from=frontend-build /frontend/js/ static/js/

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
