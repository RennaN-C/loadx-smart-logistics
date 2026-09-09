FROM node:22.23.1-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY index.html tsconfig.json vite.config.ts ./
COPY src/ ./src/
COPY public/ ./public/
COPY scripts/check-bundle-budget.mjs ./scripts/
RUN chown -R node:node /app

USER node

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
