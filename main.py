from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Doxen AI Voice API is running!"}
