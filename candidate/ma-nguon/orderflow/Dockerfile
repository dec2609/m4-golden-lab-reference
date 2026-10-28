# Base descriptors resolved on 2026-10-19; these are OCI index digests, not app image IDs.
FROM node:24-alpine@sha256:44fce696f38ba8c987c4db89954051000bbd05ffd8d8659ba15ed4a8602e937f AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY src ./src
# Public browser configuration only; runtime browser traffic must remain same-origin.
ENV VITE_API_URL="" VITE_USE_MOCK=false
RUN npm run build

FROM nginx:1.30.6-alpine@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5 AS runtime
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER 101:101
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:8080/index.html || exit 1
ENTRYPOINT ["nginx", "-g", "daemon off;"]
