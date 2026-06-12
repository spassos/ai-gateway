# Gateway = imagem oficial do LiteLLM + nossa config.
# Pinar a tag: a API admin (/user/new, /key/generate) muda entre versões.
FROM ghcr.io/berriai/litellm:main-v1.74.3-stable

COPY config.yaml /app/config.yaml

CMD ["--config", "/app/config.yaml", "--port", "4000"]
