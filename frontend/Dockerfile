FROM node:24-alpine AS development
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM development AS production
RUN npm run build
ENV NODE_ENV=production
CMD ["npm", "run", "start"]
