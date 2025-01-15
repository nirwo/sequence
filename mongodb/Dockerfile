FROM mongo:latest

COPY init/01-init.js /docker-entrypoint-initdb.d/

# Set proper permissions
RUN chmod 755 /docker-entrypoint-initdb.d/01-init.js
