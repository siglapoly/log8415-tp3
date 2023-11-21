import boto3 
import os
import paramiko
import botocore
import sys
from botocore.exceptions import ClientError

# Function to deploy the orchestrator in instance via SSH
def deploy_orchestrator():
    orchestrator_infos = get_instance_infos()
    if orchestrator_infos is not None: 
        instance_id, public_ip = orchestrator_infos   
        start_orchestrator(instance_id, public_ip, 'bot.pem')
    else:
        print("Failed to get orechestrator informations")

# Function to copy the orchestrator app code, install install dependencies, and start the orchestrator  
def start_orchestrator(instance_id, public_ip, key_file):
    try:
        # Copy the necessary files to start the flask app on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r flask_orchestrator.py info.json ubuntu@{public_ip}:/home/ubuntu'
        print(f'Copying local Flask app code to {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to start the flask_orchestrator app 
        commands = [
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'sudo apt install python3-venv -y',
            'mkdir flask_application && cd flask_application',
            'sudo python3 -m venv venv',
            'echo "----------------------- activate venv environment ------------------------------"',
            'source venv/bin/activate',
            'cd ..',
            'mv flask_orchestrator.py info.json ./flask_application',
            'cd flask_application',
            'sudo pip install Flask',
            'export flask_application=flask_orchestrator.py',
            'echo "----------------------- lunching flask app --------------------------------------"',
            'nohup sudo python3 flask_orchestrator.py > /dev/null 2>&1 &'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(stderr.read().decode('utf-8'))
        print(f'-------------- successfuly started orchestrator ---------------------------\n')  
        ssh_client.close()


# Function to get orchestrator instance id and public IP address 
def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # The orchestrator is located in AvailabilityZone us-east-1a !!
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] == 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                return (instance_id,public_ip)
            
    return None

if __name__ == '__main__':
    global ec2
    global aws_console
    
    print(" \n")          
    
    if len(sys.argv) != 5:
        print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
        sys.exit(1)

    aws_access_key_id = sys.argv[1]
    aws_secret_access_key = sys.argv[2]
    aws_session_token = sys.argv[3]
    aws_region = sys.argv[4]
    
    # Create a a boto3 session with credentials 
    aws_console = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token, 
        region_name=aws_region
    )
    # Client for ec2 instances
    ec2 = aws_console.client('ec2')

    deploy_orchestrator()  