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
#sleep 1m added inside lunch_ec2.py file

echo "---------- Creating config files for sql cluster ------------"

# Runs script to deploy the flask application
python3 create_config_files.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"


echo "---------- Deploying sql cluster on t2.micro instances ------------"
# Runs the script to lunch the elastic load balancing 
cluster_ips=$(python3 start_sql_cluster.py)
echo "Cluster IPs: $cluster_ips"
sleep 1m

echo "---------- Deploying proxy on t2.large instance ------------"
python3 launch_proxy.py "$cluster_ips"

echo "---------- AAAAAAAAAAAAAAAAAA ------------"




# Keep the terminal open after the script execution is finished
exec $SHELL


