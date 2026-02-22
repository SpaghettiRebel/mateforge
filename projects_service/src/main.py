from fastapi import FastAPI

app = FastAPI(
    title="Projects service",
    description="User's projects microservice",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok"}
