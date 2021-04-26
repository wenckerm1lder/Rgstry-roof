FROM python:3.9-buster

ENV DB_UPDATE_CRON=db-update
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y cron vim gosu && \
    groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser -s /sbin/nologin appuser && \
    touch /var/log/cron.log && \
    chown appuser:appuser /var/log/cron.log

COPY --chown=appuser:appuser . /home/appuser/cincanregistry
COPY db-update.cron "/etc/cron.d/$DB_UPDATE_CRON"

USER appuser

WORKDIR /home/appuser/cincanregistry

ENV PATH=${PATH}:/home/appuser/.local/bin

RUN pip3 install . 

USER root

ENTRYPOINT ["bash", "/home/appuser/cincanregistry/entrypoint.sh"]


