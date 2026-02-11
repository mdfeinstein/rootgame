# Stage 1: Build the React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy package.json and install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy the rest of the frontend code and build
COPY frontend/ ./
# Set production environment variables for the build
# VITE_DJANGO_URL is empty to ensure root-relative paths
RUN echo "VITE_API_URL=/api" > .env && \
    echo "VITE_DJANGO_URL=" >> .env

RUN npm run build

# Stage 2: Build the Django Backend
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (if any needed for Pillow/Postgres, though using sqlite for now)
# libpq-dev is good to have if switching to postgres later, headers for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . /app/

# Copy built frontend assets from the previous stage
# Typically vite builds to dist/, we need to copy that to where Django expects static files
# or where Whitenoise can serve them.
# We'll copy to a 'frontend_build' directory and assume settings.py is configured to collect from there
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Collect static files
# We need strictly the static files to be collected to STATIC_ROOT
# Docker build phase might not have DB access, so ensure collectstatic doesn't try to connect to DB
# or set dummy env vars for the build command.
RUN python manage.py collectstatic --noinput --clear

# Expose port (ensure Gunicorn binds to 0.0.0.0:8000)
EXPOSE 8000

# Run entrypoint
# Using sh -c to allow variable expansion if needed, but simple CMD is fine.
CMD ["gunicorn", "rootGame.wsgi:application", "--bind", "0.0.0.0:8000"]
