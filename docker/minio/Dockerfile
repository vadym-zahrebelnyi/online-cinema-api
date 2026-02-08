FROM alpine:latest

RUN apk add --no-cache curl dos2unix minio-client && \
    ln -s /usr/bin/mcli /usr/bin/mc

COPY setup_minio.sh /bin/setup_minio.sh

RUN dos2unix /bin/setup_minio.sh && chmod +x /bin/setup_minio.sh

ENTRYPOINT ["/bin/setup_minio.sh"]