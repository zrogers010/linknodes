FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine

RUN addgroup -S appuser && adduser -S appuser -G appuser

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

USER appuser

ENV PORT=8080
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
