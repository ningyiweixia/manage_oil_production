ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}

RUN mkdir -p /var/log/nginx /etc/nginx/ssl /var/cache/nginx/client_temp \
    && rm -f /etc/nginx/conf.d/default.conf \
    && chown -R nginx:nginx /var/log/nginx /var/cache/nginx /etc/nginx/conf.d

COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/conf.d/ /etc/nginx/conf.d/

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || exit 1
