ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}

RUN apk add --no-cache tzdata ca-certificates \
    && mkdir -p /var/log/nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx /var/cache/nginx
