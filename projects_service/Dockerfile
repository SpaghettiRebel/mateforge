FROM python:3.12-slim as builder

WORKDIR /build
RUN pip install grpcio-tools

COPY protos/ /build/protos/

RUN mkdir -p /build/generated
RUN python -m grpc_tools.protoc \
    -I/build/protos \
    --python_out=/build/generated \
    --grpc_python_out=/build/generated \
    /build/protos/users.proto

FROM python:3.12-slim

WORKDIR /app

COPY projects_service/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/generated/ /app/projects_service/src/infrastructure/generated/

COPY projects_service/ /app/projects_service/

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8001

CMD ["uvicorn", "projects_service.src.main:app", "--host", "0.0.0.0", "--port", "8001"]