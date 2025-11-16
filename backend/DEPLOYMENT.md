# Deployment Guide

Production deployment guide for the Agentic Observability Backend.

---

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [AWS Deployment](#aws-deployment)
5. [Security Considerations](#security-considerations)
6. [Monitoring & Logging](#monitoring--logging)
7. [Scaling](#scaling)
8. [Backup & Recovery](#backup--recovery)

---

## Deployment Options

### Quick Comparison

| Option | Complexity | Scalability | Cost | Best For |
|--------|-----------|-------------|------|----------|
| Docker | Low | Medium | Low | Small teams, dev/staging |
| Kubernetes | High | High | Medium | Production, large scale |
| AWS ECS | Medium | High | Medium | AWS infrastructure |
| VM/Bare Metal | Medium | Low | Variable | Legacy systems |

---

## Docker Deployment

### 1. Create Dockerfile

Already provided in the repository. Review and customize if needed:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-dev

# Copy application code
COPY app ./app
COPY data ./data

# Create log directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Build the Image

```bash
docker build -t agentic-observability-backend:latest .
```

### 3. Run the Container

```bash
docker run -d \
  --name agentic-backend \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  agentic-observability-backend:latest
```

### 4. Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: agentic-backend
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GEMINI_MODEL_ID=${GEMINI_MODEL_ID}
      - TEMPERATURE=${TEMPERATURE}
      - MAX_TOKENS=${MAX_TOKENS}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Add MCP Server
  mcp-server:
    image: your-mcp-server:latest
    container_name: mcp-server
    ports:
      - "3100:3100"
    restart: unless-stopped
    depends_on:
      - backend

networks:
  default:
    name: agentic-network
```

Run with:

```bash
docker-compose up -d
```

### 5. Verify Deployment

```bash
# Check container status
docker ps

# View logs
docker logs -f agentic-backend

# Test API
curl http://localhost:8000/
```

---

## Kubernetes Deployment

### 1. Create ConfigMap for Configuration

`k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-backend-config
  namespace: observability
data:
  GEMINI_MODEL_ID: "gemini-2.0-flash-exp"
  TEMPERATURE: "0.7"
  MAX_TOKENS: "8192"
```

### 2. Create Secret for API Key

```bash
kubectl create secret generic agentic-backend-secrets \
  --from-literal=GOOGLE_API_KEY='your-api-key-here' \
  -n observability
```

### 3. Create Persistent Volume

`k8s/pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agentic-backend-data
  namespace: observability
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
```

### 4. Create Deployment

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-backend
  namespace: observability
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentic-backend
  template:
    metadata:
      labels:
        app: agentic-backend
    spec:
      containers:
      - name: backend
        image: your-registry/agentic-observability-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: agentic-backend-secrets
              key: GOOGLE_API_KEY
        - name: GEMINI_MODEL_ID
          valueFrom:
            configMapKeyRef:
              name: agentic-backend-config
              key: GEMINI_MODEL_ID
        - name: TEMPERATURE
          valueFrom:
            configMapKeyRef:
              name: agentic-backend-config
              key: TEMPERATURE
        - name: MAX_TOKENS
          valueFrom:
            configMapKeyRef:
              name: agentic-backend-config
              key: MAX_TOKENS
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: agentic-backend-data
      - name: logs
        emptyDir: {}
```

### 5. Create Service

`k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentic-backend-service
  namespace: observability
spec:
  selector:
    app: agentic-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 6. Create Ingress (Optional)

`k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentic-backend-ingress
  namespace: observability
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - observability.yourdomain.com
    secretName: observability-tls
  rules:
  - host: observability.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agentic-backend-service
            port:
              number: 80
```

### 7. Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace observability

# Apply all resources
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n observability
kubectl get svc -n observability

# View logs
kubectl logs -f deployment/agentic-backend -n observability
```

---

## AWS Deployment

### Option 1: AWS ECS with Fargate

1. **Push image to ECR:**

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name agentic-observability-backend

# Tag and push
docker tag agentic-observability-backend:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/agentic-observability-backend:latest
  
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/agentic-observability-backend:latest
```

2. **Create ECS Task Definition:**

```json
{
  "family": "agentic-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/agentic-observability-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GEMINI_MODEL_ID",
          "value": "gemini-2.0-flash-exp"
        }
      ],
      "secrets": [
        {
          "name": "GOOGLE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:google-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/agentic-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

3. **Create ECS Service with ALB**

### Option 2: AWS EC2

1. Launch EC2 instance (t3.medium or larger)
2. SSH into instance
3. Install Docker and dependencies
4. Follow Docker deployment steps above

### Option 3: AWS Lambda (for serverless)

Not recommended for this application due to long-running workflows. Use ECS/EKS instead.

---

## Security Considerations

### 1. API Keys & Secrets

**Never commit secrets to git!**

```bash
# Use environment variables
export GOOGLE_API_KEY="your-key"

# Or use secret management
# - AWS Secrets Manager
# - Kubernetes Secrets
# - HashiCorp Vault
```

### 2. Network Security

- Use HTTPS/TLS for all connections
- Implement API authentication (JWT, OAuth)
- Use security groups/firewall rules
- Enable CORS only for trusted origins

### 3. Rate Limiting

Add rate limiting middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/workflows/start")
@limiter.limit("5/minute")
async def start_workflow(request: Request):
    pass
```

### 4. Input Validation

- Validate all inputs
- Sanitize log data
- Limit request sizes
- Implement timeouts

### 5. Logging & Auditing

- Log all API requests
- Monitor for suspicious activity
- Implement audit trails
- Encrypt logs at rest

---

## Monitoring & Logging

### 1. Application Logs

```python
# Configure structured logging
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### 2. Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }
```

### 3. Prometheus Metrics

Add prometheus client:

```python
from prometheus_client import Counter, Histogram, generate_latest

workflow_counter = Counter('workflows_total', 'Total workflows')
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 4. External Monitoring

- **Datadog**: Application performance monitoring
- **New Relic**: Full stack observability
- **Sentry**: Error tracking
- **CloudWatch**: AWS monitoring

---

## Scaling

### Horizontal Scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentic-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentic-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Load Balancing

- Use ALB/NLB in AWS
- Use Ingress Controller in Kubernetes
- Use NGINX for on-prem

### Caching

Add Redis for caching:

```python
import redis
cache = redis.Redis(host='localhost', port=6379)

@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    # Check cache first
    cached = cache.get(f"workflow:{workflow_id}")
    if cached:
        return json.loads(cached)
    # ... fetch from DB
```

---

## Backup & Recovery

### 1. Data Backup

```bash
# Backup feedback data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Upload to S3
aws s3 cp backup-$(date +%Y%m%d).tar.gz s3://your-bucket/backups/
```

### 2. Automated Backups

```bash
# Cron job for daily backups
0 2 * * * /path/to/backup-script.sh
```

### 3. Disaster Recovery

- Keep backups in multiple regions
- Document recovery procedures
- Test recovery regularly
- Maintain runbooks

---

## Environment-Specific Configurations

### Development

```bash
LOG_LEVEL=DEBUG
RELOAD=true
WORKERS=1
```

### Staging

```bash
LOG_LEVEL=INFO
RELOAD=false
WORKERS=2
```

### Production

```bash
LOG_LEVEL=WARNING
RELOAD=false
WORKERS=4
ACCESS_LOG=true
```

---

## Troubleshooting

### High Memory Usage

- Increase container memory limits
- Implement pagination for large results
- Clear caches regularly

### Slow Response Times

- Scale horizontally
- Add caching layer
- Optimize database queries
- Profile with cProfile

### Connection Errors

- Check network policies
- Verify firewall rules
- Test DNS resolution
- Check service endpoints

---

## Checklist

Before going to production:

- [ ] Secrets managed securely
- [ ] HTTPS/TLS enabled
- [ ] Authentication implemented
- [ ] Rate limiting configured
- [ ] Monitoring set up
- [ ] Logging configured
- [ ] Backups automated
- [ ] Health checks working
- [ ] Load testing done
- [ ] Documentation complete
- [ ] Incident response plan ready
- [ ] Rollback procedure documented

---

## Support

For deployment issues:
- Check logs: `tail -f logs/app.log`
- Review documentation
- Contact: avinash.rai@example.com

---

**Last Updated**: November 2025

