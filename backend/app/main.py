from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import endpoints
from app.api.v1 import feedback_endpoints

app = FastAPI(
    title="Multi-Agent Orchestration System with Reinforcement Learning",
    description="AI-powered observability system that learns from feedback",
    version="2.0.0"
)

# Configure CORS
# origins =

app.add_middleware(
    CORSMiddleware,
    allow_origins=['0.0.0.0'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routers
app.include_router(endpoints.router, prefix="/api/v1")
app.include_router(feedback_endpoints.router, prefix="/api/v1", tags=["Reinforcement Learning"])

@app.get("/")
def read_root():
    return {
        "status": "Backend is running",
        "features": [
            "Multi-Agent Orchestration",
            "Reinforcement Learning",
            "Human-in-the-Loop Feedback",
            "In-Context Learning"
        ],
        "version": "2.0.0"
    }