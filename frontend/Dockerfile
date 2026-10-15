FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Adresse publique du backend, intégrée au build (ex. https://sunutribunal-backend.up.railway.app/api)
ARG VITE_API_URL
RUN test -n "$VITE_API_URL" || (echo "VITE_API_URL manquante : adresse du backend /api" && exit 1)
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Modèle : ${PORT} est remplacé au démarrage (Railway fournit PORT, 80 par défaut)
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV PORT=80
EXPOSE 80
