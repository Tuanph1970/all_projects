# React Production Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Build arguments for environment configuration
ARG REACT_APP_API_URL=http://localhost:8004
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

# Install dependencies
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:1.25-alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check (use 127.0.0.1 instead of localhost to avoid IPv6 issues in Alpine)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
