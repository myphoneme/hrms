# auth-service image. Build context is backend/ (Readiness doc §2, Rule 2):
#   docker build -f services/auth-service/Dockerfile backend/
# Coolify: Base Directory /backend, Dockerfile services/auth-service/Dockerfile,
# watch paths backend/services/auth-service/**, backend/python-libs/**, backend/constraints.txt
#
# Migrations ship inside the image: run `python -m auth_service.migrate` as a deploy step (as teamora_migrator).

FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY constraints.txt ./
COPY python-libs/teamora_common ./python-libs/teamora_common
COPY services/auth-service ./services/auth-service
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -c constraints.txt ./python-libs/teamora_common ./services/auth-service

FROM python:3.12-slim AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /opt/venv /opt/venv
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app
EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '3001'), timeout=4)"
CMD ["python", "-m", "auth_service"]
