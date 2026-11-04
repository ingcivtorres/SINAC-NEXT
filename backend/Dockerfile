FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin sinac

COPY --chown=sinac:sinac . .
RUN mkdir -p /app/media && chown sinac:sinac /app/media

USER sinac

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
