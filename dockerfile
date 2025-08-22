FROM python:3.13.7-slim

WORKDIR /app/

ARG GIT_BRANCH=unknown GIT_REVISION=unknown DATE=unknown TARGET_ARCH='amd'
ENV GIT_BRANCH=$GIT_BRANCH GIT_REVISION=$GIT_REVISION DATE=$DATE LOG_LEVEL="info" TARGET_ARCH=$TARGET_ARCH
VOLUME ["/app/.cache"]
EXPOSE 80

COPY requirements /app/
COPY *.py /app/
COPY frontend/* /app/frontend/
COPY params/params_sample.ini /app/setup/params.ini
COPY entrypoint.sh restic /app/

RUN python3 -m pip install -r requirements

ENTRYPOINT ["/app/entrypoint.sh"]