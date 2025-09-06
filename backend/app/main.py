from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import endpoints

app = FastAPI(title="Multi-Agent Orchestration System")

# Configure CORS
# origins =

app.add_middleware(
    CORSMiddleware,
    allow_origins=['0.0.0.0'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "Backend is running"}