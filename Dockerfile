FROM python:3.12-slim

LABEL maintainer="InkKeeper"
LABEL description="打印机喷头自动保养程序"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       cups cups-daemon cups-client \
       printer-driver-escpr \
       ghostscript curl \
    && rm -rf /var/lib/apt/lists/* \
    && cupsctl --remote-admin --remote-any 2>/dev/null || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data/uploads

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

EXPOSE 5000

CMD ["/app/start.sh"]
