FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_API_URL
# Only write .env.production (which Vite reads automatically) when a build
# arg was actually passed. An ENV var set to "" would still be a defined
# key and short-circuit api.ts's `?? "/api"` fallback, since "" is not
# undefined -- leaving the file absent is what makes VITE_API_URL genuinely
# undefined to import.meta.env when no override is given.
RUN if [ -n "$VITE_API_URL" ]; then echo "VITE_API_URL=$VITE_API_URL" > .env.production; fi
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
