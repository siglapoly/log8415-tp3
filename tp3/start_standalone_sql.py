import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

def deploy_standalone_sql():

    instance_infos = get_instance_infos()
    print(instance_infos)
    #we keep first instance for the standalone sql
    instance = instance_infos[0]
    instance_id, public_ip = instance
    start_standalone_sql(instance_id,'bot.pem')
    pass


def start_standalone_sql(instance_id, key_file):
    try:

        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        print(public_ip)
        # Copy the sakila db files to instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} sakila-db.tar.gz ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying sakila database files (.tar.gz) to standalone sql on {instance_id}...')
        os.system(copy_command)
        print('copy command executed successfully')
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            'echo "----------------------- RUNNING COMMANDS ON INSTANCE FOR STANDALONE SQL ----------------------------------"',

            'sudo apt-get update -y',
            'sudo apt-get install mysql-server -y',

            'echo "----------------------- decompress sakila database files----------------------------------"',
            'sudo tar -xvzf sakila-db.tar.gz',
            'sudo sleep 5',
            #'echo "----------------------- connect to mySQL and run in background, Create and populate database ----------------------------------"',
            #'nohup sudo mysqld > /home/ubuntu/mysql.log 2>&1 &',
            #THIS ONE WORKS
            #'nohup sudo mysqld > /home/ubuntu/mysql.log 2>&1 & nohup sudo mysql -u root -e "source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql; use sakila;" > /home/ubuntu/db_setup.log 2>&1 &',
            

            #TRY THIS ONE FOR ADDING USER
            "nohup sudo mysqld > /home/ubuntu/mysql.log 2>&1 & nohup sudo mysql -u root -e \"source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql; use sakila; CREATE USER 'simon'@'localhost' IDENTIFIED BY 'your_password'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'localhost' WITH GRANT OPTION; FLUSH PRIVILEGES;\" > /home/ubuntu/db_setup.log 2>&1 &",
            
            
            #'echo "----------------------- connect to mySQL and run in background ----------------------------------"',
            #'sudo sleep 5',
            #'echo "----------------------- Create and populate database ----------------------------------"',
            #'nohup sudo mysql -u root "source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql; use sakila;" > /home/ubuntu/db_setup.log 2>&1 &',
        ]  
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly started the standalone sql server ---------------------------\n')  
        ssh_client.close()


def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance in zone us-east-1a is the standalone_sql 
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] == 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                instance_id_list.append((instance_id,public_ip))
            
    return instance_id_list


if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script install and start a standalone sql server on the first instance \n")          
    
    #print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDEQ4BXXAWH'
    aws_secret_access_key='X994ECzr2iqSq0+NJqzy3SLQIhhOVYHhf5Klxk48'
    aws_session_token='FwoGZXIvYXdzENz//////////wEaDIRtVFGMHnjx5UnvjCLIARmSq5wDgk7LzyPJLkyEJyI4+0vgh4EER16/AoLn5a2pbhw9iaBIGT8QCsUHC7dBYXHLaaX7/T6XP8utNVs7JAYVvx2rCRtvWOUsD00zUR3ZtHQY3sbGPXDTOKr07VRqwCxRvtRBMcqW/efnxBbnR7CGXAlmjHaQRnBWag49rDqCHZxJoWFcRWLBP0siGjYltKjkjEo6+Mksb301RLJv902x+NEkqmRjrJ1bZvE/c8Qd5wlDJCaK+o/vqQw49sUALtoYDmkJDvX0KPz6rasGMi1OMdQNbJUyfyq3WdFIKY9Ue+IpSxRqm60epAlyu+3DSHVLaqRYGJfHLhz3U+w='
    aws_region = 'us-east-1'


    # Create a a boto3 session with credentials 
    aws_console = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token, 
        region_name=aws_region
    )
    # Client for ec2 instances
    ec2 = aws_console.client('ec2')

    deploy_standalone_sql()

