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

            #'echo "----------------------- connect to mySQL and run in background ----------------------------------"',
            'nohup sudo mysqld > /home/ubuntu/mysql.log 2>&1 &',

            'sudo sleep 5',
            #'echo "----------------------- Create and populate database ----------------------------------"',
            'nohup sudo mysql -u root "source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql; use sakila;" > /home/ubuntu/db_setup.log 2>&1 &',
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
             # The instance in zone us-east-1a is for the orchestrator, so we don't need its information
            if instance['State']['Name'] == 'running':# and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
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
 
    aws_access_key_id='ASIAQDC3YUDE5CRBDKCG'
    aws_secret_access_key='Bvf8mHQVbiDcvHdbK5qg5nZkXSyQbumH+d1Kbhhf'
    aws_session_token='FwoGZXIvYXdzEAgaDL1gcmGbaeJ3XpLtqCLIAVVublv4T8mAockFZJeYS41lNAt/ecWMGLsmSIxwM5nQqD+RghPQ/MOYWN86C8hik1li8EqdHPR0B5hbTKvJO2F3ggCfeXIqOJhd4UWR6+X/qjNKES8X2jzbBNgYN3ZF1osK8m2OvEpgySxxDihi+WjOOeM/dLVNgql3aNuG8rlr+WrjEnID3e47mdPlZGMIliONl9Exdepj6y2niMqLPCp1ACQGG2cWyFpTgA8oyOdiA3LBhvCbY+1Y3R3CCH6Gp4a13vPT2EO8KPmn/6oGMi22pIPIJJHtGuCdAq9reUTayGybK69LqVB48F1lbiQrqLG+sORa6i+NVmr4uHs='
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

