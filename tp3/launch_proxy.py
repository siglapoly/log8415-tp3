import boto3 
import os
import botocore
import platform
import subprocess
import sys
import time 
import paramiko
from botocore.exceptions import ClientError
import json

def launch_proxy(mgmt_ip, data_nodes_ips):
    try:
        proxy_flask_directory = 'proxy_flask_application'

        instance_infos = get_instance_infos()
        instance_id, public_ip, private_ip, zone = instance_infos[0] #instance 7 is proxy

        #create proxy app file
        create_proxy_app_file(instance_id, proxy_flask_directory, mgmt_ip, data_nodes_ips)
        
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id]) #could remove this here and add ip as f param
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        copy_command = f"scp -o StrictHostKeyChecking=no -i 'bot.pem' -r {proxy_flask_directory} ubuntu@{public_ip}:/home/ubuntu/"
        print(f'Copying local Flask app code to {instance_id}...')
        os.system(copy_command)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename='bot.pem')
        print(f'connected to instance {public_ip} via ssh')
        #Commands to install needed packages and run Flask app in background
        commands = ['echo "----------------------- instaling packages ----------------------------------"',
            'sudo apt-get update && sudo apt-get upgrade -y ',
            'sudo apt-get install python3-pip -y',
            'sudo apt-get install python3 -y',
            f'cd {proxy_flask_directory}',
            'sudo python3 -m venv venv',
            'echo "----------------------- activate venv environment ------------------------------"',
            'source venv/bin/activate',
            'sudo pip install Flask',
            'sudo pip install requests',
            'export flask_application = proxy.py',
            'echo "----------------------- lunching flask app --------------------------------------"',
            'nohup sudo python3 proxy.py > /dev/null 2>&1 &',

        ]

        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        ssh_client.close()


def create_proxy_app_file(instance_id, proxy_flask_directory, mgmt_ip, data_nodes_ips) : 
    os.makedirs(proxy_flask_directory,exist_ok=True)
    print('CREATING PROXY APP FILE')
    create_file = f'''cat <<EOF > {proxy_flask_directory}/proxy.py
from flask import Flask, request
import requests
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def forward_request():
    if request.method == 'POST':
        # Forward GET request to mgmt_ip
        response = requests.get(f'http://{mgmt_ip}', headers=request.headers, data=request.get_data())
    elif request.method == 'GET':
        # Forward POST request to a randomly selected data node
        selected_ip = 'http://' + str(random.choice({data_nodes_ips}))
        response = requests.post(selected_ip, headers=request.headers, data=request.get_data())
    else:
        # Handle other HTTP methods if needed
        response = None

    if response:
        # Return the response from the target server to the original requester
        return response.content, response.status_code, response.headers.items()
    else:
        return "Unsupported HTTP method", 400

if __name__ == '__main__':
    # Listen on port 80 for external traffic
    app.run(host='0.0.0.0', port=80, debug=True)

EOF'''     
    os.system(create_file)


def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             if instance['State']['Name'] == 'running' and instance.get('InstanceType') == 't2.large': 
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                private_ip = instance.get('PrivateIpAddress')
                zone = instance.get('Placement', {}).get('AvailabilityZone')

                instance_id_list.append((instance_id,public_ip,private_ip,zone))
            
    return instance_id_list


if __name__ == '__main__':
    global ec2
    global aws_console

    #print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDE6DNFAXGH'
    aws_secret_access_key='vuHbVB0aCelchDy1Mybq5i0REDuY8XJg3GbV1PBS'
    aws_session_token='FwoGZXIvYXdzEEUaDHHsBNRYXNWf8YXiKCLIAYCPotbwPJwRZgM3eSJgMc9Agd7FVw1wDFXpZawWxgwGOKihnJx0TgfKtdBkhAV2Lvnz+PvaKxDvb110IOR6lOQ3IbchrbcG7VeiCZiALlmzblwhhTBF2EvO9115ePuSJwoEHCG64YWxaUeOQow0b5p+ScaW9ldCn7WahIiovRnD/Vf6nKx3IDJFWo4AgdCr1qQ+Eljv3/9I2f8fxUZbRfo3BQZ7Rbblz2tbqLSG8xH6uAYX+FmCiVrejnOxZjPeC4QdxJ+b6uyHKN2l/asGMi3j+Luq2pX4kf/rAExKpgujJ2HB51s0a6oCWyxt64g9VhgUZonZAZAR4ctF3Gk='
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

    # Access the file path from command-line arguments
    file_path = sys.argv[1]

    # Read the JSON data from the file
    with open(file_path, 'r') as file:
        output_json = file.read()
    
    # Parse the JSON string into a Python dictionary
    output_dict = json.loads(output_json)

    # Access individual elements from the dictionary
    mgmt_ip = output_dict.get("mgmt_ip")
    data_nodes_ips = output_dict.get("data_nodes_ips")


    # Continue with your second script logic...
    print(f"Management IP: {mgmt_ip}")
    print(f"Data Nodes IPs: {data_nodes_ips}")

    launch_proxy(mgmt_ip, data_nodes_ips)