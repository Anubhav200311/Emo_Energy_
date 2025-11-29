from fastapi import FastAPI
from routers import auth
from config import settings


app = FastAPI(
    title= settings.APP_NAME,
    settings= settings.APP_VERSION,
    description="An intelligent API that processes content using AI",
)


# Include Routers
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
