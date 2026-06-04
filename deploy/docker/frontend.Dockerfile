ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}

RUN addgroup -S webapp -g 10002 \
    && adduser -S webapp -G webapp -u 10002 \
    && mkdir -p /usr/share/nginx/html /var/cache/nginx /var/run/nginx \
    && chown -R webapp:webapp /usr/share/nginx/html /var/cache/nginx /var/run/nginx /etc/nginx

COPY deploy/frontend-dist/ /usr/share/nginx/html/
COPY deploy/nginx/frontend-site.conf /etc/nginx/conf.d/default.conf

USER webapp

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
