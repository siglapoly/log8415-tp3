import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

def deploy_standalone_sql():

    instance_infos = get_instance_infos()

    #we keep first instance for the standalone sql
    instance = instance_infos[0]
    instance_id, public_ip = instance
    start_standalone_sql(instance_id,public_ip,'bot.pem')
    pass


def start_standalone_sql(instance_id, key_file):
    try:

        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']

        # Copy the sakila db files to instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} sakila-db.tar.gz ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying sakila database files (.tar.gz) to standalone sql on {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            'echo "----------------------- RUNNING COMMANDS ON INSTANCE FOR STANDALONE SQL ----------------------------------"'

            'sudo apt-get update -y',
            'sudo apt-get install mysql-server',

            'echo "----------------------- decompress sakila database files----------------------------------"',
            'tar -xvzf sakila-db.tar.gz',

            'echo "----------------------- connect to mySQL----------------------------------"',
            'sudo mysql -u root',

            'echo "----------------------- Create and populate database ----------------------------------"',
            'SOURCE /home/ubuntu/sakila-db/sakila-schema.sql;',
            'SOURCE /home/ubuntu/sakila-db/sakila-data.sql;',  
            #'USE sakila;',#
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
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                instance_id_list.append((instance_id,public_ip))
            
    return instance_id_list


f __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script install and start a standalone sql server on the first instance \n")          
    
    #print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDEUN3Q52UU'
    aws_secret_access_key='UIPTih4VxGKaA/3Woqxsy1Jy3V7hVRiUqzKGkWHQ'
    aws_session_token='FwoGZXIvYXdzENj//////////wEaDC1FxNDYpH29nFYWuyLIAYWtJ+NDUp6pQbW1hzcb6CvlU1XsuFam/kywvFCIRM+Bc6wg3pDoLeNLsIVQnOxNmMFTZt0wCTDB4oxmHu859RZBp1oj73yT7S425I6RD6kHTTTi6u7HsW/yzm1EV0wczryjlRLS7nFeO1vD4+IPRCZnVdyIhAuSxJ2eFvEYNPRV4ZgqkyKU1MqtHFzuT8mLv6tPJw/p0K30J2yXRxy/RhO9NSEFBEzDeD7V6CWKiuXdIvSwkCgxn70bymk6pbdM00KfiWh1SA80KMHi9KoGMi0ZIO2umB5cJXbrbc9QrpCYgHWwKn/oNH6/t/+JyaIklV0QEnt2itIhuVkWZGI='
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

