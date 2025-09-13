# Agentic Infrastucture Observablity with Google Gemini

- This project is a complete full-stack application that demonstrates a multi-agent AI system.
- The backend is built with **FastAPI** and uses **Microsoft's Semantic Kernel** to orchestrate multiple AI agents powered by **Google's Gemini API**. 
- The frontend is an interactive **Streamlit** dashboard that visualizes the agents' collaboration in real-time. 
- The entire application is containerized with **Docker** for easy setup and deployment.

---
## System Design 
<div>
    <img src="https://github.com/avinfinity/agentic-observability/blob/main/System_Design.png"/>
</div>

## Data Flow Diagram
<div>
    <img src="https://github.com/avinfinity/agentic-observability/blob/main/FlowDiagram.png" /> 
  
</div>

## MTTR Improvements
<div>
    <img src="https://github.com/avinfinity/agentic-observability/blob/main/MTTR_Comparision.png" />
</div>

## Radar Chart Comparisions
<div>
   <img src="https://github.com/avinfinity/agentic-observability/blob/main/radar_plot.png"/> 
</div>

---

## 🏛️ Project Architecture

The project is structured as a monorepo with two distinct services:

* **`backend/`**: A FastAPI application that serves the core AI logic. It exposes a REST API to start workflows and an SSE endpoint to stream live updates.

* **`frontend/`**: A Streamlit application that provides the user interface. It communicates with the backend via API calls and visualizes the real-time data it receives.

```

multi-agent-system/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app.py
│   ├── components/
│   ├── services/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── docker-compose.yml
└── README.md

```

