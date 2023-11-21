import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

# Function to deploy the ML app in instance via SSH and save the containers informations in the file info.json
def deploy_models():
    instance_infos = get_instance_infos()
    index = 1
    for instance in instance_infos :   
        instance_id, public_ip = instance   
        start_containers(instance_id, public_ip, 'bot.pem')
        containers = {f'container{index}': {'ip':public_ip, "port":"5000", "status": "free"},f'container{index+1}': {'ip':public_ip, "port":"5001", "status": "free"}}
        write_intance_infos("info.json",containers)
        index += 2 

# Function to copy the ML app code, install docker, and start containers in the instance  
def start_containers(instance_id, public_ip, key_file):
    try:
        # Copy the necessary files to start the containers on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r ./containers ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying local Flask app code and Dockerfile to {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            'echo "----------------------- adding Dockers official GPG key ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install ca-certificates curl gnupg -y',
            'sudo install -m 0755 -d /etc/apt/keyrings',
            'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'sudo chmod a+r /etc/apt/keyrings/docker.gpg',
            'echo "----------------------- adding the repository to Apt sources ----------------------------------"',
            'echo \
                "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
                sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            'sudo apt-get update -y',
            'echo "----------------------- instaling Docker packages and Docker compose ----------------------------------"',
            'sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y',
            'sudo apt-get install docker-compose-plugin',
            'echo "----------------------- starting containers ----------------------------------"',
            'cd containers',
            'sudo docker compose up -d'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly started two containers and application running ---------------------------\n')  
        ssh_client.close()

def write_intance_infos(file_path, instance_info):
    try:
        with open(file_path, 'r') as file:
            # Check if the file is empty
            file_content = file.read()
            if not file_content:
                data = {}
            else:
                # Load the existing data from the file
                data = json.loads(file_content)
        
        data.update(instance_info)
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f'File "{file_path}" with {instance_info} updated successfully.')

    except FileNotFoundError:
        with open(file_path, 'w') as file:
            json.dump(instance_info, file, indent=4)
        
        print(f'File "{file_path}" created successfully.')

    except Exception as e:
        print(f'Error: {e}')

# Function to get workers instance id and public IP address 
def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance in zone us-east-1a is for the orchestrator, so we don't need its information
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                instance_id_list.append((instance_id,public_ip))
            
    return instance_id_list


if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script install Docker and start two containers on every instances \n")          
    
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

    deploy_models()  