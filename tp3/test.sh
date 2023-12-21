# Install required libraries
pip install boto3 awscli paramiko
apt-get install jq

echo "------- Credentials added succesfully  ----------"

echo "---------- Launch EC2 ----------------------------"
# Call the Python script to lunch ec2 instances
python3 lunch_ec2.py #"$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

#echo "---------- Launch standalone sql ----------------------------"
#std_ip=$(python3 start_standalone_sql.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION")

#echo "---------- Launch sysbench benchmark for standalone sql, results savec standalone_sysbench_output.log----------------------------"
#ssh -i bot.pem ubuntu@"$std_ip" "sudo sysbench --db-driver=mysql --mysql-user=root --mysql-db=sakila --table-size=10000 /usr/share/sysbench/oltp_read_only.lua run" > standalone_sysbench_output.log

echo "---------- Creating config files for sql cluster ------------"
python3 create_config_files.py #"$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

echo "---------- Deploying sql cluster on t2.micro instances ------------"
# Runs the script to lunch the elastic load balancing 
python3 start_sql_cluster.py #"$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION")
echo "Cluster IPs: $cluster_ips"
sleep 1m

echo "---------- Launch sysbench benchmark for sql cluster ------------"
#mgmt_public_ip=$(jq -r '.mgmt_public_ip' cluster_ips.json)
#ssh -i bot.pem ubuntu@${mgmt_public_ip} "sudo sysbench --db-driver=mysql   --mysql-host=${mgmt_public_ip}   --mysql-user=simon   --mysql-password=nomis   --mysql-db=sakila   --table-size=10000   /usr/share/sysbench/oltp_read_only.lua run > sysbench_cluster_output.log"

echo "---------- Deploying proxy on t2.large instance ------------"
python3 launch_proxy.py "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION" "$cluster_ips"
echo "Proxy IPs (private, public): $cluster_ips"


echo "---------- Deploying gatekeeper on two t2.large instances------------"
python3 launch_gatekeeper.py 


# Keep the terminal open after the script execution is finished
exec $SHELL
