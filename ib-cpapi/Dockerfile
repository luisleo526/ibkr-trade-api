FROM openjdk:8u212-jre-alpine3.9
WORKDIR /app

RUN apk add wget curl && \
    wget https://download2.interactivebrokers.com/portal/clientportal.gw.zip && \
    unzip clientportal.gw.zip -d . && \
    rm clientportal.gw.zip && \
    apk del wget
RUN apk add openrc --no-cache
RUN mkdir -p /log

COPY conf.yaml /conf.yaml
COPY runtime.cron /runtime.cron
COPY runtime.sh /runtime.sh

RUN chmod 0644 /runtime.cron
RUN chmod +x /runtime.sh
RUN crontab /runtime.cron
EXPOSE 5000
CMD crond && sh bin/run.sh /conf.yaml