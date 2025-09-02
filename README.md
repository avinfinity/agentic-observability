Here is the raw Markdown content of the `README.md` file, without any extra formatting, so you can copy and paste it directly.

```
# Multi-Agent AI System with FastAPI, Streamlit, and Gemini

This project is a complete full-stack application that demonstrates a multi-agent AI system. The backend is built with **FastAPI** and uses **Microsoft's Semantic Kernel** to orchestrate multiple AI agents powered by **Google's Gemini API**. The frontend is an interactive **Streamlit** dashboard that visualizes the agents' collaboration in real-time. The entire application is containerized with **Docker** for easy setup and deployment.

---

## ✨ Features

* **Decoupled Architecture:** A high-performance FastAPI backend for AI logic, completely separate from the Streamlit frontend for the user interface.

* **Multi-Agent Orchestration:** Utilizes Semantic Kernel to manage a workflow between specialized agents (Monitoring, Analysis, Remediation) coordinated by a master Orchestrator agent.

* **Real-Time Visualization:** The frontend displays a live, graphical representation of the agent workflow, showing which agent is active and the handoffs between them.

* **Live Event Streaming:** Employs Server-Sent Events (SSE) for efficient, real-time communication from the backend to the frontend.

* **Containerized:** Fully containerized with Docker and orchestrated with Docker Compose for a simple, one-command startup.

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

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Docker**: <https://docs.docker.com/get-docker/>

* **Docker Compose**: <https://docs.docker.com/compose/install/> (usually included with Docker Desktop)

---

## 🚀 Getting Started

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

```

git clone \<your-repository-url\>
cd multi-agent-system

```

### 2. Configure Environment Variables

The application requires API keys and configuration settings, which are managed through `.env` files. Example files are provided.

#### A. Backend Configuration

First, obtain a Google Gemini API Key:

1. Go to https://aistudio.google.com/.

2. Click on "Get API key" and create a new API key.

3. Copy the key.

Now, create the backend `.env` file:

```

# Navigate to the backend directory

cd backend

# Copy the example file to create your own .env file

cp .env.example .env

```

Open the newly created `backend/.env` file and add your Google Gemini API key:

```

# backend/.env

GOOGLE\_API\_KEY="your-google-gemini-api-key"
GEMINI\_MODEL\_ID="gemini-1.5-pro-latest"

```

#### B. Frontend Configuration

The frontend does not require any secrets, but the `.env` file structure is included for consistency. You can simply copy the example file.

```

# Navigate back to the project root, then to the frontend directory

cd ../frontend

# Copy the example file

cp .env.example .env

```

The `BACKEND_URL` is set automatically by `docker-compose.yml` and does not need to be in this file.

### 3. Build and Run the Application

With the environment variables configured, you can start the entire application with a single command from the project's root directory.

```

# Make sure you are in the root directory of the project

cd ..

# Build the Docker images and start the services

docker-compose up --build

```

This command will:

* Build the Docker images for both the backend and frontend services.

* Create a shared network for the containers.

* Start both containers.

### 4. Access the Application

Once the containers are running, you can access the services:

* **Streamlit Frontend**: Open your web browser and navigate to `http://localhost:8501`

* **FastAPI Backend Docs**: To see the API documentation, navigate to `http://localhost:8000/docs`

## ⚙️ How to Use

1. Open the Streamlit application at `http://localhost:8501`.

2. You will see a text area pre-filled with a sample system issue. You can use this or enter your own.

3. Click the "**🚀 Start Agent Workflow**" button.

4. The application will start the backend process and begin receiving real-time updates.

5. On the right side, the **Agent Workflow Visualization** will light up, showing the Orchestrator agent starting the process. As agents are called (Monitoring, Analysis, etc.), their corresponding nodes and the edges leading to them will change color to indicate activity.

6. On the left side, under **Live Event Logs**, you can expand each event to see the raw JSON data being streamed from the backend.

## 🛑 Stopping the Application

To stop the running application and remove the containers, press `Ctrl + C` in the terminal where `docker-compose` is running. Then, run:

```

docker-compose down

```

This will stop and remove the containers and the network created by Docker Compose.
```