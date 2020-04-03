FROM python:3.8-alpine

WORKDIR /app

ADD ./ ./

RUN apk --no-cache add git && \
    apk --no-cache add gcc musl-dev libffi-dev openssl-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    git clone https://github.com/msb/fs.googledrivefs.git --branch file_id_support /tmp/fs.googledrivefs && \
    pip install /tmp/fs.googledrivefs

VOLUME /app
VOLUME /data

ENTRYPOINT ["python3", "sunnyportal-download.py"]