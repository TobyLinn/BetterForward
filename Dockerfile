FROM python:3.12-alpine

ARG VERSION=1.0.0
LABEL version="${VERSION}"
LABEL org.opencontainers.image.version="${VERSION}"

WORKDIR /app

COPY VERSION /app/VERSION
COPY locale /app/locale
COPY requirements.txt /tmp/requirements.txt

# 安装字体支持（用于生成验证码图片）
RUN apk add --no-cache \
    ca-certificates \
    ttf-dejavu \
    fontconfig \
    && update-ca-certificates \
    && fc-cache -f

RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt \
    && mkdir -p /app/data \
    && find /app/locale -name '*.po' -type f -delete

ADD main.py /app
ADD src /app/src
ADD db_migrate /app/db_migrate

ENV TOKEN=""
ENV GROUP_ID=""
ENV LANGUAGE="en_US"
ENV TG_API=""
ENV WORKER="2"

CMD python -u /app/main.py -token "$TOKEN" -group_id "$GROUP_ID" -language "$LANGUAGE" -tg_api "$TG_API" -worker "$WORKER"
