FROM python:3.9-buster

RUN apt-get update && apt-get install -y cron && \
    groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser -s /sbin/nologin appuser

COPY --chown=appuser:appuser . /home/appuser/cincanregistry

USER appuser

WORKDIR /home/appuser/cincanregistry

ENV PATH=${PATH}:/home/appuser/.local/bin

RUN echo $PATH && pip3 install . 


ENTRYPOINT ["cincanregistry"]
CMD ["--help"]


