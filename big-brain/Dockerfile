FROM node:22-alpine AS client-build
WORKDIR /app
COPY package.json package-lock.json* ./
COPY client/package.json ./client/
RUN npm install --workspace=client
COPY client ./client
RUN npm run build --workspace=client

FROM node:22-alpine AS server-build
WORKDIR /app
COPY package.json package-lock.json* ./
COPY server/package.json ./server/
RUN npm install --workspace=server
COPY server ./server
RUN npm run build --workspace=server

FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
COPY server/package.json ./server/
RUN npm install --workspace=server --omit=dev
COPY --from=server-build /app/server/dist ./server/dist
COPY --from=client-build /app/client/dist ./client/dist
ENV PORT=3002
ENV VAULT_PATH=/app/data/vault
ENV DB_PATH=/app/data/vault-flow.db
EXPOSE 3002
CMD ["node", "server/dist/index.js"]
