from fastapi import FastAPI

app = FastAPI(title="Gateway")

@app.get("/health")
def health():
    return {"status": "ok"}