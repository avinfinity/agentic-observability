FROM node:20-bullseye-slim

WORKDIR /app

# Reduce npm noise in builds
ENV npm_config_update_notifier=false \
    npm_config_fund=false \
    npm_config_audit=false

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install -g npm@11.9.0 && npm ci

# Copy source
COPY . .

EXPOSE 3100

# Run restart script at container start
RUN chmod +x /app/restart.sh
ENTRYPOINT ["/app/restart.sh"]
