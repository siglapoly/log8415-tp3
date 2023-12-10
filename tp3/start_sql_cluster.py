import boto3 
import os
import botocore
import platform
import subprocess
import sys
import paramiko
from botocore.exceptions import ClientError

def start_cluster_sql():
    instance_infos = get_instance_infos()

    #first run common steps across all nodes
    print('RUNNING COMMON STEPS ON ALL NODES!')
    for instance in instance_infos : 
        instance_id, public_ip, private_ip, zone = instance
        #run_common_steps(instance_id,'bot.pem')
    print('FINISHED RUNNING COMMON STEPS ON ALL NODES')

    #Start mgmt node
    for instance in instance_infos : 
        instance_id, public_ip, private_ip, zone = instance
        if zone == 'us-east-1b': #mgmt node
            print('STARTING MGMT NODE')
            #start_mgmt_node(instance_id,'bot.pem')
            print('MGMT NODE STARTED')
            mgmt_ip = 'ip-' + private_ip.replace('.','-') + '.ec2.internal:1186' #get ip of mgmt node to give to data nodes
            print(mgmt_ip)                                      #clean this up so it is a output of start_mgmt func
        else:
            pass
    #Start data nodes
    for instance in instance_infos : 
        instance_id, public_ip, private_ip, zone = instance
        if zone in ['us-east-1c', 'us-east-1d', 'us-east-1e']: #data nodes for cluster
            print('STARTING DATA NODE')
            start_data_node(instance_id,'bot.pem',mgmt_ip)
            print('DATA NODES STARTED')
        else:
            pass
    #Back on mgmt node
    for instance in instance_infos : 
        instance_id, public_ip, private_ip, zone = instance
        if zone == 'us-east-1b': #mgmt node
            print('STARTING MGMT NODE')
            #start_mgmt_node(instance_id,'bot.pem')
            print('MGMT NODE STARTED')
            mgmt_ip = 'ip-' + private_ip.replace('.','-') + '.ec2.internal:1186' #get ip of mgmt node to give to data nodes
            print(mgmt_ip)                                      #clean this up so it is a output of start_mgmt func
        else:
            pass    

def run_common_steps(instance_id, key_file):
    try:
        #print('Running common steps on )
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        print(public_ip)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
        'sudo service mysqld stop',
        'sudo apt-get remove mysql-server mysql mysql-devel',
        'sudo mkdir -p /opt/mysqlcluster/home',
        'cd /opt/mysqlcluster/home',
        'sudo wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'sudo tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'sudo ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc',
        "sudo bash -c 'echo \export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc > /etc/profile.d/mysqlc.sh'",
        "sudo bash -c 'echo \export PATH=$MYSQLC_HOME/bin:$PATH >> /etc/profile.d/mysqlc.sh'",
        'source /etc/profile.d/mysqlc.sh',
        'sudo apt-get update && sudo apt-get -y install libncurses5 ',
        
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly ran common steps on node {public_ip} ---------------------------\n')  
        ssh_client.close()


def start_mgmt_node(instance_id, key_file):
    try:
        #print('Starting mySQL cluster management node')
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        print(public_ip)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
        'sudo apt-get update && sudo apt-get -y install libncurses5',
        'sudo mkdir -p /opt/mysqlcluster/deploy',
        'cd /opt/mysqlcluster/deploy',
        'sudo mkdir conf',
        'sudo mkdir mysqld_data',
        'sudo mkdir ndb_data',
        'sudo chmod o+w /opt/mysqlcluster/deploy/conf/', #give write and copy rights to any user so that we can copy config files
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(f'-------------- successfuly started the management node of mySQL cluster ---------------------------\n')  
    finally:
        print(stdout.read().decode('utf-8'))  
        ssh_client.close()

    try:
        # Copy the config files to mgmt instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} my.cnf config.ini ubuntu@{public_ip}:/opt/mysqlcluster/deploy/conf'
        print(f'Copying config files to standalone sql on {instance_id}...')
        os.system(copy_command)
        print('copy command executed successfully')

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh - actions2')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            'cd /opt/mysqlcluster/home/mysqlc',
            'sudo groupadd mysql',
            'sudo useradd -g mysql mysql',
            'sudo chown -R mysql:mysql /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64/data/',
            'sudo chmod -R 777 /opt/mysqlcluster/', #give rights to all folder
            'scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data --general-log',
            'sudo chmod 600 /opt/mysqlcluster/deploy/conf/config.ini'
            'sudo /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf',
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print('SUCESSS')
    finally:
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly started the management node of mySQL cluster ---------------------------\n')  
        ssh_client.close()

def start_data_node(instance_id, key_file,mgmt_ip):
    try:
        #print('Running common steps on )
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        #print(public_ip)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        print(f'XXX {mgmt_ip}')
        commands = [
            'sudo groupadd mysql',
            'sudo useradd -g mysql mysql',
            'sudo chown -R mysql:mysql /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64/data/',
            'sudo chmod -R 777 /opt/mysqlcluster/', #give rights to all folder
            'sudo mkdir -p /opt/mysqlcluster/deploy/ndb_data',
            f'nohup sudo /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64/bin/ndbd -c {mgmt_ip} > /dev/null 2>&1 &'

        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print('IT WORKED')
    finally:
        print(stdout.read().decode('utf-8'))
        ssh_client.close()


def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance in zone us-east-1a is the standalone_sql, us-east-1b is mgmt and other data nodes 
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                private_ip = instance.get('PrivateIpAddress')
                zone = instance.get('Placement', {}).get('AvailabilityZone')

                instance_id_list.append((instance_id,public_ip,private_ip,zone))
            
    return instance_id_list


if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script install and start the mySQL cluster \n")          
    
    #print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDE6GTLHQFC'
    aws_secret_access_key='eHIrJagxVvdzsC6HHiKm7t5rjzTY871Du4sbo0gB'
    aws_session_token='FwoGZXIvYXdzEIj//////////wEaDH8UXS/ZMv76Y2CroyLIAVnE3j5vqqyfC7IjvH/2xJAbd1xUfZ1fnJqcU1qxlOuWuSUDKLc7K/Bsn1n7cfHV25erU3/x7AUqnLg6L5FmvxC0P6g2caQz5ypDsosvWTiHmO9NH2Xe8NwbubFkMc0URMgFN9X2zA6PVleuswKZ7A/yZL9nNft0DprLF9CISX6hZWa2P6XCdHRxMTb9ryPNou6FqRpqY0bSHJpD09LZXUbyEWFMpSBpf2VZD/UooSHRPHkCcbRWk+Jj/LQXDhoMoZ24MokjC4rnKNrQ06sGMi12/Ko+wUKrx+P+OiS2w3iTZB435avTXhJjbFic3rWyWzDEg1FnkCfUpk6lK1s='
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

    start_cluster_sql()