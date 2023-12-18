
# Install required libraries
pip install boto3 awscli paramiko



echo "---------- Lunch EC2 ----------------------------"

# Call the Python script to lunch ec2 instances
#python3 lunch_ec2.py

echo "---------- Creating config files for sql cluster ------------"

# Runs script to deploy the flask application
python3 create_config_files.py

echo "---------- Deploying sql cluster on t2.micro instances ------------"
# Runs the script to lunch the elastic load balancing 
python3 start_sql_cluster.py
#cluster_ips=$(cat cluster_ips.json) 
#echo "Cluster IPs: $cluster_ips"
sleep 10

echo "---------- Deploying proxy on t2.large instance ------------"
python3 launch_proxy.py "cluster_ips.json"

echo "---------- AAAAAAAAAAAAAAAAAA ------------"

# Keep the terminal open after the script execution is finished
exec $SHELL