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

def launch_gatekeeper(proxy_ip, trusted_ips):

    #get numeric version of proxy ip to use for trusted security group for trusted host
    proxy_ip_num = proxy_ip[3:15].replace('-','.')

    th_flask_directory = 'th_flask_application'
    gate_flask_directory = 'gate_flask_application'

    #get instance infos
    instance_infos = get_instance_infos()
    
    #get trusted host ip to give to gate
    instance_id, public_ip, private_ip, zone = instance_infos[1] #instance 5 trusted host, 6 will be gate (so we can input th ip)
    th_ip = 'ip-' + private_ip.replace('.','-') + '.ec2.internal'

    #launch gate
    instance_id, public_ip, private_ip, zone = instance_infos[2] #instance 6 is gate
    print(f'STARTING gate NODE on ip (public,private) :{public_ip,private_ip}')
    launch_gate(instance_id,'bot.pem',gate_flask_directory,th_ip, trusted_ips)
    print(f'gate NODE STARTED on ip (public,private) :{public_ip,private_ip}')

    #get gate ip and sg id to safely secure trusted host
    gate_ip = private_ip
    response = ec2.describe_instances(InstanceIds=[instance_id])
    sg_gate_id = [group['GroupId'] for group in response['Reservations'][0]['Instances'][0]['SecurityGroups']][0]

    #launch trusted host allowing all traffic for now so we can launch it (original security group)
    instance_id, public_ip, private_ip, zone = instance_infos[1] #instance 5 trusted host
    print(f'STARTING th NODE on ip (public,private) :{public_ip,private_ip}')
    launch_trusted_host(instance_id,'bot.pem',th_flask_directory, proxy_ip)
    print(f'th NODE STARTED on ip (public,private) :{public_ip,private_ip}')

    #create custom security group for trusted host (only accepting request coming from gate)    
    print(f'Proxy ip : {proxy_ip}')
    print(f'Th ip : {th_ip}')
    print(f'Gate ip : {gate_ip}')
    print(f'Proxy ip num: {proxy_ip_num}')
    
    sg_th_id = create_security_group_for_host(gate_ip,sg_gate_id, proxy_ip_num)
    print(f'New security group ID is {sg_th_id} allowing only traffic from gate from ip {gate_ip} and from proxy from ip {proxy_ip}')
    time.sleep(10)

    #apply security group to trusted host
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[sg_th_id]
    )

    authorize_traffic_between_sg(sg_gate_id, sg_th_id)
    authorize_traffic_between_sg(sg_th_id, sg_gate_id)
    

    

def authorize_traffic_between_sg(source_sg_id, destination_sg_id):
    try:
        
        response_outbound = ec2.authorize_security_group_egress(
            GroupId=source_sg_id,
            IpPermissions=[
                {
                    'IpProtocol': '-1',  # All traffic
                    'UserIdGroupPairs': [
                        {
                            'GroupId': destination_sg_id,
                        },
                    ],
                },
            ],
        )
        
        
    except Exception as e:
        print(e)


def launch_gate(instance_id,key_file, flask_directory, th_ip, trusted_ips):
    try:
        #create gate app file  
        create_gate_app_file(flask_directory, th_ip, trusted_ips)
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id]) #could remove this here and add ip as f param
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r {flask_directory} ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying local Flask app code to {instance_id}...')
        os.system(copy_command)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print(f'connected to instance {public_ip} via ssh')
        #Commands to install needed packages and run Flask app in background
        commands = ['echo "----------------------- instaling packages ----------------------------------"',
            'sudo apt-get update && sudo apt-get upgrade -y ',
            'sudo apt-get install python3-pip -y',
            'sudo apt-get install python3 -y',
            f'cd {flask_directory}',
            'sudo python3 -m venv venv',
            'echo "----------------------- activate venv environment ------------------------------"',
            'source venv/bin/activate',
            'sudo pip install Flask',
            'sudo pip install requests',
            'export flask_application = gate.py',
            'echo "----------------------- lunching flask app --------------------------------------"',
            'nohup sudo python3 gate.py > /dev/null 2>&1 &',

        ]

        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        ssh_client.close()


def launch_trusted_host(instance_id, key_file, flask_directory, proxy_ip):
    try:
        create_th_app_file(flask_directory, proxy_ip)
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id]) #could remove this here and add ip as f param
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r {flask_directory} ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying local Flask app code to {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print(f'connected to instance {public_ip} via ssh')
        #Commands to install needed packages and run Flask app in background
        commands = ['echo "----------------------- instaling packages ----------------------------------"',
            'sudo apt-get update && sudo apt-get upgrade -y ',
            'sudo apt-get install python3-pip -y',
            'sudo apt-get install python3 -y',
            f'cd {flask_directory}',
            'sudo python3 -m venv venv',
            'echo "----------------------- activate venv environment ------------------------------"',
            'source venv/bin/activate',
            'sudo pip install Flask',
            'sudo pip install requests',
            'export flask_application=trusted_host.py',

            'echo "----------------------- kill unused services ------------------------------"',
            'lsof -i :53 | awk \'NR>1 {{print $2}}\' | xargs sudo kill',
            'lsof -i :68 | awk \'NR>1 {{print $2}}\' | xargs sudo kill',
            'lsof -i :323 | awk \'NR>1 {{print $2}}\' | xargs sudo kill',

            'echo "----------------------- lunching flask app --------------------------------------"',
            'nohup sudo python3 trusted_host.py > /dev/null 2>&1 &',

        ]

        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        ssh_client.close()


def create_gate_app_file(flask_app_directory, th_ip, trusted_ips) : 
    os.makedirs(flask_app_directory,exist_ok=True)
    print('CREATING GATE APP FILE')
    create_file = f'''cat <<EOF > {flask_app_directory}/gate.py
from flask import Flask, request
import requests

app = Flask(__name__)

th_url = 'http://{th_ip}:443'

@app.route('/', methods=['GET', 'POST'])
def forward_request():

    # Forward the incoming request to trusted host only if ip of request is trusted
    client_ip = request.remote_addr
    if client_ip in {trusted_ips}:
        response = requests.request(request.method, th_url + request.path, headers=request.headers, data=request.get_data())
    
        # Return the response from Flask App 2 to the original requester
        return response.content, response.status_code, response.headers.items()
    else:
        return "Unauthorized", 401

if __name__ == '__main__':
    # Listen on port 443 for external traffic
    app.run(host='0.0.0.0', port=443,debug=True)
EOF'''     
    os.system(create_file)


def create_th_app_file(flask_app_directory, proxy_ip) : 
    os.makedirs(flask_app_directory,exist_ok=True)
    create_file = f'''cat <<EOF > {flask_app_directory}/trusted_host.py
from flask import Flask, request
import requests

app = Flask(__name__)

proxy_url = 'http://{proxy_ip}:443'

@app.route('/', methods=['GET', 'POST'])
def forward_request():

    # Forward the incoming request to the proxy

    response = requests.request(request.method, proxy_url + request.path, headers=request.headers, data=request.get_data())

    # Return the response from proxy to the original requester
    return response.content, response.status_code, response.headers.items()

if __name__ == '__main__':
    # Listen on port 443 for external traffic
    app.run(host='0.0.0.0', port=443,debug=True)
EOF'''    
    os.system(create_file)

    
def create_security_group_for_host(gate_ip, sg_gate_id, proxy_ip):
    try:
        # Create a security group allowing HTTPS (port 443) traffic only from trusted host
        response = ec2.create_security_group(
            Description='This security group is for the trusted host',
            GroupName='botSecurityGroup_trustedhost01',
        )
        security_group_id = response['GroupId']

        # Authorize inbound traffic on port 443 from both CidrIp and sg_gate_id
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': sg_gate_id,
                        },
                    ],
                    'IpRanges': [
                        {
                            'CidrIp': f'{gate_ip}/32',
                            'CidrIp': f'{proxy_ip}/32'
                        },
                    ],
                },
            ],
        )
        return security_group_id
        
    except Exception as e:
        if "InvalidGroup.Duplicate" in str(e):
            response = ec2.describe_security_groups(
            Filters=[
            {
                'Name': 'group-name',
                'Values': ['botSecurityGroup_trustedhost3']
                    }
                ]
            )
            return response['SecurityGroups'][0]['GroupId']
        else:
            print(f"Failed to create security group {e}")


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
    
    #GET PROXY IP ---------------------------------
    # Access the file path from command-line arguments
    proxy_ips_path = 'proxy_ips.json'

    # Read the JSON data from the file
    with open(proxy_ips_path, 'r') as file:
        output_json = file.read()

    # Parse the JSON string into a Python dictionary
    output_dict = json.loads(output_json)

    # Access individual elements from the dictionary
    proxy_ip = output_dict.get("proxy_private_ip")
    proxy_ip = 'ip-' + proxy_ip.replace('.','-') + '.ec2.internal'
    print(f'The proxy IP that will receive requests forwarded by gatekeeper is: {proxy_ip}')

    #GET TRUSTED IPS------------------------------
    trusted_ips_file = 'trusted_ips.txt'
    with open(trusted_ips_file, 'r') as file:
    # Read lines from the file and create a list
        trusted_ips = [line.strip() for line in file.readlines()]
    print(f'The trusted ips by the gate are : {trusted_ips}')

    #LAUNCH GATEKEEPER ----------------------------
    ec2 = aws_console.client('ec2')
    launch_gatekeeper(proxy_ip,trusted_ips)


