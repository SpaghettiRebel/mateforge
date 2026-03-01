from fastapi import FastAPI

app = FastAPI(
    title="Portfolio service",
    description="Users' personal portfolio microservice",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok"}
