FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY}
RUN npm install

COPY frontend/ ./

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    UNI_INPUT_DIR=/app \
    UNI_OUTPUT_DIR=/app/unpackage/dist/build/h5

RUN npm run build:h5

FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/unpackage/dist/build/h5/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
