FROM python:3.12-slim

WORKDIR /app

COPY portfolio_service/requirements.txt requirements.txt
RUN python3 -m pip install --upgrade pip && pip install -r requirements.txt

COPY portfolio_service/ /app/portfolio_service/

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8002

CMD ["uvicorn", "portfolio_service.src.main:app", "--host", "0.0.0.0", "--port", "8002"]

