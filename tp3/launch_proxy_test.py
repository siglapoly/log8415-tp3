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

def launch_proxy():#mgmt_ip, data_nodes_ips):
    try:
        proxy_flask_directory = 'proxy_flask_application'

        instance_infos = get_instance_infos()
        instance_id, public_ip, private_ip, zone = instance_infos[0] #instance 7 is proxy

        #create proxy app file
        create_proxy_app_file(proxy_flask_directory)#, mgmt_ip, data_nodes_ips)
        
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
    return public_ip, private_ip

def create_proxy_app_file(proxy_flask_directory):#, mgmt_ip, data_nodes_ips) : 
    os.makedirs(proxy_flask_directory,exist_ok=True)
    print('CREATING PROXY APP FILE')
    create_file = f'''cat <<EOF > {proxy_flask_directory}/proxy.py
from flask import Flask, request
import requests
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    return 'Hello, World! FROM PROXY '

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

    '''
    print(" \n")          
    
    if len(sys.argv) != 5:
        print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
        sys.exit(1)

    aws_access_key_id = sys.argv[2]
    aws_secret_access_key = sys.argv[3]
    aws_session_token = sys.argv[4]
    aws_region = sys.argv[5]
    '''
 
    aws_access_key_id='ASIAQDC3YUDEX6Q2PXWQ'
    aws_secret_access_key='6dUFJuljb+gozJnSTo5c3ngOzVwFQajlJIi5iGU8'
    aws_session_token='FwoGZXIvYXdzEJH//////////wEaDD5zzUBYh0Zq10mXEiLIAXnPYjCAoxDjS7C0qDjOzTkthaEZdF4X/laVynyvBJmf3EAabE5HmxI9AU0jsfWxh/x7BuzSEcmnG29QG+u9lAqNstdZnG9i55uRvoYwYsQoIEF+PClYfqaJ3TX8tgV19vHNLXhQ2NzPotoqlIuuXwrcgRe7sz/ld0vuv7tmfISa9lvaEbiBC2asv1n8MiGUDbqwa99XeoxNzKpaw9uE4MuDQzI7LwxljECayuVqNParmuX0FzjQFxJBh8vaPZa4FfIixd4gBlxZKN78jawGMi2gMtjbrb3ba9hTSx3qfgCLHR395cCIpC+xT/SqDaTwPIEJn3YYf92mTo4d0qM='
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
    '''
    # Access the file path from command-line arguments
    cluster_ips_path = sys.argv[1]

    # Read the JSON data from the file
    with open(cluster_ips_path, 'r') as file:
        output_json = file.read()
    
    # Parse the JSON string into a Python dictionary
    output_dict = json.loads(output_json)

    # Access individual elements from the dictionary
    mgmt_ip = output_dict.get("mgmt_ip")
    data_nodes_ips = output_dict.get("data_nodes_ips")
    
    # Continue with your second script logic...
    print(f"Management IP: {mgmt_ip}")
    print(f"Data Nodes IPs: {data_nodes_ips}")
    ''' 
    proxy_public_ip, proxy_private_ip = launch_proxy()#:mgmt_ip, data_nodes_ips)

    print(f'Proxy ips : {proxy_private_ip, proxy_public_ip}')

    #output private and public ip of proxy to feed to gatekeeper
    output_dict = {
        "proxy_private_ip": proxy_private_ip,
        "proxy_public_ip": proxy_public_ip,
    }

    # Write the dictionary to a JSON file
    with open('proxy_ips.json', 'w') as json_file:
        json.dump(output_dict, json_file)
    