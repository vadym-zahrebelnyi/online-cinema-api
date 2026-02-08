# Stage 1: Copy the script from the root context
FROM alpine:latest AS script_copier
WORKDIR /app
COPY commands/setup_minio.sh /app/setup_minio.sh

# Stage 2: Build the minio_setup image
FROM alpine:latest
RUN apk add --no-cache curl dos2unix minio-client && \
    ln -s /usr/bin/mcli /usr/bin/mc

COPY --from=script_copier /app/setup_minio.sh /bin/setup_minio.sh

RUN dos2unix /bin/setup_minio.sh && chmod +x /bin/setup_minio.sh

ENTRYPOINT ["/bin/setup_minio.sh"]