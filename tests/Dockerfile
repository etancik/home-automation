FROM ghcr.io/home-assistant/home-assistant:2026.9.2
COPY tests/requirements.txt /tmp/test-requirements.txt
RUN uv pip install --system --index-strategy unsafe-best-match -r /tmp/test-requirements.txt
WORKDIR /workspace
ENTRYPOINT ["python", "-m", "pytest"]
ENV PYTHONPATH=/usr/src/homeassistant
