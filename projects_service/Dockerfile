FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python3 -m pip install --upgrade pip && pip install -r requirements.txt

COPY . auth_service/

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "auth_service.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

