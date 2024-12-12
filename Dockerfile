# Use an official Python image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y nginx && apt-get clean

# Copy the submodules
COPY ./scan /app/scan
COPY ./focus /app/focus

# Install Python dependencies for both apps
WORKDIR /app/scan
RUN pip install -r requirements.txt

WORKDIR /app/focus
RUN pip install -r requirements.txt

# Copy the Nginx configuration
COPY ./nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for Nginx
EXPOSE 80

WORKDIR /app

# Start both apps and Nginx
CMD uvicorn scan.main:app --host 0.0.0.0 --port 8000 & \
    uvicorn focus.server:app --host 0.0.0.0 --port 8001 & \
    nginx -g "daemon off;"
