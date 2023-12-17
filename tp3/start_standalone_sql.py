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
        'sudo service mysql stop',  # Stop MySQL service before making changes
        'sudo apt-get update -y',
        'sudo apt-get install mysql-server -y',

        'echo "----------------------- decompress sakila database files----------------------------------"',
        'sudo tar -xvzf sakila-db.tar.gz',
        # Start MySQL in the background, source Sakila files, create users, and flush privileges
        #"sudo mysqld > /home/ubuntu/mysql.log 2>&1",

        'sudo sed -i "s/^bind-address\\s*=\\s*127.0.0.1/bind-address = 0.0.0.0 /" /etc/mysql/mysql.conf.d/mysqld.cnf',
        #"sudo mysql -u root -e \"source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql; use sakila; CREATE USER 'simon'@'localhost' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'localhost' WITH GRANT OPTION; CREATE USER 'simon'@'%' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;\" > /home/ubuntu/db_setup.log 2>&1 &",
        'echo -e "\nn\nn\nn\nY\nn\n" | sudo mysql_secure_installation',
        #install sakila db
       # "sudo mysql -u root -e \"source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql;\" > /home/ubuntu/db_setup.log 2>&1",
        
        #login in root, create user (local instance and also from anywhere (%)) and give rights, 
        #"sudo mysql -u root -e \"USE sakila; CREATE USER 'simon'@'localhost' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'localhost' IDENTIFIED BY 'nomis'; CREATE USER 'simon'@'%' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'%' IDENTIFIED BY 'nomis'; FLUSH PRIVILEGES;\" > /home/ubuntu/db_setup.log 2>&1",
        


        #'sudo sleep 5',
        #'echo -e "\nn\nn\nn\nY\nn\n" | sudo mysql_secure_installation',
        #'sudo sleep 5',
        #'sudo sed -i "s/^bind-address\\s*=\\s*127.0.0.1/bind-address = 0.0.0.4/" /etc/mysql/mysql.conf.d/mysqld.cnf',
   
    
        #'sudo service mysql restart',  # Restart MySQL service after making bind address python3 schanges
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
 
    aws_access_key_id='ASIAQDC3YUDEV6RN2DQ4'
    aws_secret_access_key='tJcJm+zC3+Rx2/acFmRi0cLxjpiJZu2PMEhnQ3Vl'
    aws_session_token='FwoGZXIvYXdzECwaDMq9XgD0uv8Oao0qSyLIAankAq11SYRtkVTPBZTqTqq1xLvq7Gn/pDs+6uanLb5bB1TwU5VAzwxvXX/sM6E1hFvB33lVPbk2ftEyX1axe3G/vcIRTizJfzJxHctgPhnWo2ue9txuTDc21B/wTT/6RcX645+yxfA7uf0C1BKLS0BDJzlBgZwBUMMWhcoXTb562zWAW9mLPEFLMNX0rzr/yP0HOsGp8WLVnE9GvjP9PBE+xGvkF/2mnr2Igvp5j0+NF+Xv9uY5/anDzxqOy2RNJBgQqxvVIrFNKMjR96sGMi3YiLmtoNb0YpDc5WigOtf5oOhVwfD9GhsKFz0N6EK31xj6sbbvUCsylnSjyf4='
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

