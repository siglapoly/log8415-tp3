#!/bin/bash

# Install required libraries
pip install boto3 awscli paramiko
apt-get install jq

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

echo "---------- Launch EC2 ----------------------------"
# Call the Python script to lunch ec2 instances
python3 lunch_ec2.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

echo "---------- Launch standalone sql ----------------------------"
std_ip=$(python3 start_standalone_sql.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION")

echo "---------- Launch sysbench benchmark for standalone sql, results savec standalone_sysbench_output.log----------------------------"
ssh -i bot.pem ubuntu@"$std_ip" "sudo sysbench --db-driver=mysql --mysql-user=root --mysql-db=sakila --table-size=10000 /usr/share/sysbench/oltp_read_only.lua run" > standalone_sysbench_output.log

echo "---------- Creating config files for sql cluster ------------"
python3 create_config_files.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

echo "---------- Deploying sql cluster on t2.micro instances ------------"
# Runs the script to lunch the elastic load balancing 
cluster_ips=$(python3 start_sql_cluster.py)
echo "Cluster IPs: $cluster_ips"
sleep 1m

echo "---------- Launch sysbench benchmark for sql cluster ------------"
#mgmt_ip=$(jq -r '.mgmt_ip' cluster_ips.json)
mgmt_public_ip=$(jq -r '.mgmt_public_ip' cluster_ips.json)
ssh -i bot.pem ubuntu@${mgmt_public_ip} "sudo sysbench --db-driver=mysql   --mysql-host=${mgmt_public_ip}   --mysql-user=simon   --mysql-password=nomis   --mysql-db=sakila   --table-size=10000   /usr/share/sysbench/oltp_read_only.lua run > sysbench_cluster_output.log"
#ssh -i bot.pem ubuntu@${mgmt_public_ip} "sudo sysbench --db-driver=mysql   --mysql-host=ec2-${mgmt_public_ip//./-}.compute-1.amazonaws.com   --mysql-user=simon   --mysql-password=nomis   --mysql-db=sakila   --table-size=10000   /usr/share/sysbench/oltp_read_only.lua run > sysbench_cluster_output.log"

echo "---------- Deploying proxy on t2.large instance ------------"
python3 launch_proxy.py "$cluster_ips"

echo "---------- AAAAAAAAAAAAAAAAAA ------------"
python3 launch_gatekeeper.py 


# Keep the terminal open after the script execution is finished
exec $SHELL


