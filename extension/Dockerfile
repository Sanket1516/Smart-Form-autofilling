FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . ./
RUN npm run build

FROM alpine:3.21 AS export
COPY --from=build /app/dist /extension
CMD ["sh", "-c", "mkdir -p /app/dist && cp -R /extension/. /app/dist/"]
