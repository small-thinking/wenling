# Use an official Python runtime as a parent image
FROM python:3.10-bullseye

# Define environment variable

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app
COPY .env .
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Upgrade pip, install Poetry, and install project dependencies using Poetry
RUN pip install --upgrade pip \
    && pip install poetry==1.4.1 \
    && poetry export --without-hashes -f requirements.txt > requirements.txt \
    && pip3 install -r requirements.txt \
    && pip3 install cryptography \
    && pip3 install -e .

# Run the application
CMD ["uvicorn", "wenling.web_service:app", "--host", "0.0.0.0"]
