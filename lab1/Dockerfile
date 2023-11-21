# Python base image
FROM python:3.9

# Adding the script file to the container'S base folder
ADD analysis.py .

# Install the Python library 'requests' and 'boto3' needed to execute the script
RUN pip install requests boto3 matplotlib pandas

# Command to start the script in the container
CMD ["python3", "./analysis.py"] 