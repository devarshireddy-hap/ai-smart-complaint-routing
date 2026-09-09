# Frontend Dockerfile — multi-stage build.
# Stage 1 builds the static React bundle; Stage 2 serves it with nginx.
# No secrets are baked into the image: VITE_API_BASE_URL is a public,
# non-secret value (the backend's URL), passed at build time.

# ---- Stage 1: build ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- Stage 2: serve ----
FROM nginx:1.27-alpine AS serve

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
