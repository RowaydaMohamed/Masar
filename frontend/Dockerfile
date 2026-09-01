FROM node:22-alpine AS build

WORKDIR /app

# Install deps first so this layer is cached unless package files change
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve the static build with Nginx ----
FROM nginx:alpine AS runtime

# Remove the default Nginx welcome config and use ours (SPA fallback)
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy only the built static files, nothing else from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
