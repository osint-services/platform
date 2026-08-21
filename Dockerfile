# Use an official Python image
FROM python:3.10-slim

# Install Python dependencies and set working directory
WORKDIR /app

# Copy the service sources
COPY ./profile_checker /app/profile_checker
COPY ./profile_search /app/profile_search
COPY ./phone_search /app/phone_search
COPY ./dataset_service /app/dataset_service
COPY ./social_mapping /app/social_mapping_repo

# Install the selected service dependencies
ARG APP_DIR=profile_checker
RUN if [ "$APP_DIR" = "social_mapping" ]; then \
      pip install --no-cache-dir -r /app/social_mapping_repo/requirements.txt; \
    else \
      pip install --no-cache-dir -r /app/${APP_DIR}/requirements.txt; \
    fi

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/social_mapping_repo

EXPOSE 8000

CMD ["uvicorn", "profile_checker.main:app", "--host", "0.0.0.0", "--port", "8000"]
