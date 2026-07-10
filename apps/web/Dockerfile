# QuantCouncil web dashboard.
# Build context is apps/web itself (see infra/docker-compose.yml).

FROM node:22-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

# Install dependencies first for better layer caching.
COPY package.json ./
RUN npm install

# Copy the rest of the app and build.
COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
