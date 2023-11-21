# Python base image
FROM python:3.9-slim

# Set the working directory to /code
WORKDIR /code

# Set environment variables used by the flask command
ENV FLASK_APP=flask_model.py
ENV FLASK_RUN_HOST=0.0.0.0

# Install gcc and other dependencies
RUN apt-get update

# Copy requirements.txt and install the Python dependencies.
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Add metadata to the image to describe that the container is listening on port 80
EXPOSE 80

# Copy the application code in the project to the workdir . in the image
COPY flask_model.py .

# Set the default command for the container to flask run
CMD ["python", "flask_model.py"]