#!/bin/bash

# Install required libraries
pip install boto3 awscli paramiko


# Prompt the user for AWS credentials and other information
# Verify inputs
while true; do
  read -p "Enter your AWS Access Key ID: " AWS_ACCESS_KEY_ID
  if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "Invalid input. Please try again."
  else
    break
  fi
done

while true; do
  read -p "Enter your AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
  if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Invalid input. Please try again."
  else
    break
  fi
done

while true; do
  read -p "Enter your AWS Session Token: " AWS_SESSION_TOKEN
  if [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "Invalid input. Please try again."
  else
    break
  fi
done

# Input for AWS region (default: us-east-1)
read -p "Enter your AWS Region (default is us-east-1): " AWS_DEFAULT_REGION
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "------- Adding credentials credentials to env file -----"
ENV_FILE="env.list"
# Check if the environment file exists
if [ -e "$ENV_FILE" ]; then  

  # Modify the 'env' file with new credentials
  sed -i "s#^AWS_ACCESS_KEY_ID=.*#AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID#" "$ENV_FILE"
  sed -i "s#^AWS_SECRET_ACCESS_KEY=.*#AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY#" "$ENV_FILE"
  sed -i "s#^AWS_SESSION_TOKEN=.*#AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN#" "$ENV_FILE"
  sed -i "s#^AWS_DEFAULT_REGION=.*#AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION#" "$ENV_FILE"
else
  # Write the initial credentials to the 'env' file
  echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" > "$ENV_FILE"
  echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> "$ENV_FILE"
  echo "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN" >> "$ENV_FILE"
  echo "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION" >> "$ENV_FILE"
  echo "AWS_DEFAULT_OUTPUT=json" >> "$ENV_FILE"
fi
echo "------- Credentials added succesfully  ----------"

echo "---------- Lunch EC2 ----------------------------"

# Call the Python script to lunch ec2 instances
python3 lunch_ec2.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

# Wait for 1 minute to make sure that the instance compeleted the initialization before deploying
sleep 1m

echo "---------- Deploy flask application ------------"
# Create folder to contain the flask application file 
mkdir flask_application
# Runs script to deploy the flask application
python3 deploy_app.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

# Wait for 10 seconds to make sure that the deploy is finished
sleep 10

echo "---------- Lunch Elastic Load balancer ------------"
# Runs the script to lunch the elastic load balancing 
python3 lunch_elb.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"


# Wait for 2 minutes to make sure that the load balancer is lunched 
sleep 2m

echo "--------- Lunch benchmarking -------------------------"

# Windows:  Make sure Docker Desktop application on Windows is opened before using this script.
# Linux:  Make sure that docker service is started
# It is necessary to run Docker commands.


# Stop and remove any container build from the image 'python-analysis-script'
# before building a new image with this name.
docker stop docker rm $(docker ps -a -q --filter "ancestor=python-analysis-script")
docker rm docker rm $(docker ps -a -q --filter "ancestor=python-analysis-script")


# Build the Docker image from the Dockerfile. 
# The Dockerfile must be in the same directory than this script.
docker build -t python-analysis-script .


# Execute the created image. 
# The script analysis.py must be in the same directory than this script.
# This will run the analysis script and provide the results for the metrics.
# The environnement variables with credentials to access information of metrics
# with CLoudWatch via boto3 are in env.list file --> this file must same directory than this script.
docker run --env-file ./env.list python-analysis-script


# Get the Container ID
container_id=$(docker ps -a -q --filter "ancestor=python-analysis-script")


# Copy the files generated from the file system of the container to the file system of the host machine
docker cp $container_id:./load_balancer_stats.pdf .
docker cp $container_id:./target_stats_groupM4.pdf .
docker cp $container_id:./target_stats_groupT2.pdf .
docker cp $container_id:./load_balancer_metric_graphs.pdf .
docker cp $container_id:./target_group_metric_graphs_groupM4.pdf .
docker cp $container_id:./target_group_metric_graphs_groupT2.pdf .
docker cp $container_id:./instances_metric_graphs.pdf .


# Keep the terminal open after the script execution is finished
exec $SHELL


