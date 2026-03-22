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

RUN sed -i 's/import users_pb2 as users__pb2/from . import users_pb2 as users__pb2/g' /build/generated/users_pb2_grpc.py

FROM python:3.12-slim

WORKDIR /app

COPY auth_service/requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --from=builder /build/generated/ /app/auth_service/src/infrastructure/generated/

COPY auth_service/ /app/auth_service/

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
EXPOSE 50051

CMD ["uvicorn", "auth_service.src.main:app", "--host", "0.0.0.0", "--port", "8000"]