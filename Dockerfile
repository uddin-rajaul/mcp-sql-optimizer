# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to ensure modules can be imported
ENV PYTHONPATH=/app

# Run server.py when the container launches
# Using ENTRYPOINT allows arguments to be passed if needed
ENTRYPOINT ["python", "server.py"]
