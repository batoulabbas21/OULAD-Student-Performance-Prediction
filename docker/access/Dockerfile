FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY docker/access/requirements.txt /app/docker/access/requirements.txt
RUN pip install --no-cache-dir -r docker/access/requirements.txt \
    && useradd --create-home --uid 10001 oulad \
    && mkdir -p /app/data/processed /app/ontology /app/shapes /app/outputs \
    && chown -R oulad:oulad /app
COPY --chown=oulad:oulad src/access /app/src/access
COPY --chown=oulad:oulad src/validation/validate.py /app/src/validation/validate.py
COPY --chown=oulad:oulad src/project/serve_container.py /app/src/project/serve_container.py
COPY --chown=oulad:oulad config/access /app/config/access
USER oulad
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=180s --retries=6 \
    CMD python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)); assert r['status']=='ready'"
CMD ["python", "src/project/serve_container.py"]
