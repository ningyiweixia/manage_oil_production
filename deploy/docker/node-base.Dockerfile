ARG NODE_BASE_IMAGE=node:22-alpine
FROM ${NODE_BASE_IMAGE}

ENV NODE_ENV=production
RUN addgroup -S nodeapp -g 10003 \
    && adduser -S nodeapp -G nodeapp -u 10003 \
    && mkdir -p /opt/web \
    && chown -R nodeapp:nodeapp /opt/web
WORKDIR /opt/web
USER nodeapp
