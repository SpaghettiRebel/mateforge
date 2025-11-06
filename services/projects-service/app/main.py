import uvicorn
from fastapi import FastAPI
app = FastAPI()


@app.get("/")
def index():
    return [{"status": "ok"}, {"hotel": "trivago"}]


@app.get("/{id_num}/")
def id_echo(id_num: int):
    return [{"status": "ok", "id": f"{id_num}"}, {"modded_id": f"{id_num + 10}"}]


if __name__ == "__main__":
    uvicorn.run(app)
