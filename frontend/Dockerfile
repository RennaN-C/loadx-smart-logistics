FROM node:22.23.1-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN chown -R node:node /app

USER node

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
