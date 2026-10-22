FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 APP_ENV=production APP_DB=/data/drunken-guide.sqlite3
WORKDIR /app
COPY server/requirements.txt /app/server/requirements.txt
RUN --mount=type=secret,id=build_ca if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; pip install --no-cache-dir -r server/requirements.txt && useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
COPY --chown=app:app . /app
USER app
EXPOSE 8001
VOLUME /data
CMD ["python", "server/app.py", "serve", "--host", "0.0.0.0", "--port", "8001"]
