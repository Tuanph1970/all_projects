# Production Dockerfile for React Native web build
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies needed for native builds
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++

# Install Expo CLI
RUN npm install -g @expo/cli@latest

# Copy package files
COPY package*.json ./

# Install all dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for web
RUN npx expo export:web

# Production stage
FROM nginx:alpine

# Copy built app to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]