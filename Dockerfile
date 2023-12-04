# Use an official Python runtime as a parent image
FROM python:3.10-bullseye

# Set the working directory in the container
WORKDIR /app

# Define build-time environment variables
ARG ENVIRONMENT
ARG OPENAI_API_KEY
ARG NOTION_TOKEN
ARG NOTION_ROOT_PAGE_ID
ARG NOTION_DATABASE_ID
ARG IMGUR_CLIENT_ID
ARG PORT

ENV PORT=${PORT:-8000}

# If in production, generate .env file, else copy existing .env
RUN if [ "$ENVIRONMENT" = "prod" ]; then \
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env && \
        echo "NOTION_TOKEN=$NOTION_TOKEN" >> .env && \
        echo "NOTION_ROOT_PAGE_ID=$NOTION_ROOT_PAGE_ID" >> .env && \
        echo "NOTION_DATABASE_ID=$NOTION_DATABASE_ID" >> .env && \
        echo "IMGUR_CLIENT_ID=$IMGUR_CLIENT_ID" >> .env; \
    fi

# Copy the .env file in dev mode, else copy the rest of the files
COPY .env* ./
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE $PORT

# Upgrade pip, install Poetry, and install project dependencies using Poetry
RUN pip install --upgrade pip \
    && pip install poetry==1.4.1 \
    && poetry export --without-hashes -f requirements.txt > requirements.txt \
    && pip3 install -r requirements.txt \
    && pip3 install cryptography \
    && pip3 install -e .

# Run the application
CMD uvicorn wenling.web_service:app --host 0.0.0.0 --port $PORT
