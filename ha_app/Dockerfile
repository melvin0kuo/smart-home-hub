FROM node:24-bookworm-slim AS frontend
# 固定公開原始碼版本，避免建置時追蹤可變動的 main。
ADD https://codeload.github.com/melvin0kuo/smart-home-hub/tar.gz/b2dfa21eb34863a06d10e6ab827a5bd617a12690 /tmp/source.tar.gz
RUN mkdir /source && tar -xzf /tmp/source.tar.gz -C /source --strip-components=1
WORKDIR /source/frontend
RUN npm ci && npm run build

FROM python:3.12-slim-bookworm
ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
WORKDIR /app
COPY --from=frontend /source/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY --from=frontend /source/backend/app /app/backend/app
COPY --from=frontend /source/frontend/dist /app/frontend/dist
COPY run.py /app/run.py
EXPOSE 8000
CMD ["python", "/app/run.py"]
