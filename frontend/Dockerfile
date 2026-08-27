# 前端镜像：Vue3 构建 → Nginx 托管静态资源并反向代理 /api（《09》第 8 节）
# 构建：docker build -f frontend/Dockerfile -t <registry>/contract-risk:frontend-<tag> frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
