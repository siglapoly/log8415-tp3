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

def start_cluster_sql():

    #initialize mgmt node ip and data nodes ips so that we can feed to the proxy app
    data_nodes_ips = []

    instance_infos = get_instance_infos()

    #first run common steps across all nodes
    print('RUNNING COMMON STEPS ON ALL NODES!')
    for instance in instance_infos[1:5] : # instances 1,2,3,4 for sql cluster
        instance_id, public_ip, private_ip, zone = instance
        run_common_steps(instance_id,'bot.pem')
    print('FINISHED RUNNING COMMON STEPS ON ALL NODES')

    #Start mgmt node
    instance_id, public_ip, private_ip, zone = instance_infos[1] #instance 1 is mgmt node
    print(f'STARTING MGMT NODE on ip (public,private) :{public_ip,private_ip}')
    start_mgmt_node(instance_id,'bot.pem')
    print(f'MGMT NODE STARTED on ip (public,private) :{public_ip,private_ip}')
    mgmt_ip = 'ip-' + private_ip.replace('.','-') + '.ec2.internal:1186' #get ip of mgmt node to give to data nodes
    manag_ip = private_ip
    manag_public_ip = 'ec2-' + public_ip.replace('.','-') + '.compute-1.amazonaws.com'
    print(mgmt_ip)                                      #clean this up so it is a output of start_mgmt func

    #Start data nodes
    for instance in instance_infos[2:5] : #instances 2,3,4 for data nodes
        instance_id, public_ip, private_ip, zone = instance
        print(private_ip, zone )
        print('STARTING DATA NODE')
        start_data_node(instance_id,'bot.pem',mgmt_ip)
        print('DATA NODES STARTED')
        #save data nodes ips
        data_nodes_ips.append(private_ip)

    time.sleep(10) #wait for data nodes to all connect
    #Back on mgmt node
    instance_id, public_ip, private_ip, zone = instance_infos[1]
    print('STARTING mySQL server')
    start_mysql_server(instance_id,'bot.pem')
    print('mySQL server STARTED')

    return manag_ip, data_nodes_ips, manag_public_ip

def run_common_steps(instance_id, key_file):
    try:
        #print('Running common steps on )
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id]) #could remove this here and add ip as f param
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        #print(public_ip)
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print(f'connected to instance {public_ip} via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
        'sudo apt-get update -y',
        'sudo service mysqld stop',
        'sudo apt-get remove mysql-server mysql mysql-devel',
        'sudo mkdir -p /opt/mysqlcluster/home',
        'cd /opt/mysqlcluster/home',
        'sudo wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'sudo tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'sudo ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc',
        "echo 'export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc' | sudo tee /etc/profile.d/mysqlc.sh > /dev/null",
        "echo 'export PATH=$MYSQLC_HOME/bin:$PATH' | sudo tee -a /etc/profile.d/mysqlc.sh > /dev/null",
        'source /etc/profile.d/mysqlc.sh',
        'sudo apt-get update && sudo apt-get -y install libncurses5',
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly ran common steps on node {public_ip} ---------------------------\n')  
        ssh_client.close()

def start_mgmt_node(instance_id, key_file):
    try:
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        #print(public_ip)

        # Copy the config files to mgmt instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} my.cnf config.ini sakila-db.tar.gz ubuntu@{public_ip}:/home/ubuntu'
        print(f'Copying config files to mgmt node sql on {instance_id}...')
        os.system(copy_command)
        print('copy command executed successfully')
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
        'sudo mkdir -p /opt/mysqlcluster/deploy',
        'cd /opt/mysqlcluster/deploy',
        'sudo mkdir conf',
        'sudo mkdir mysqld_data',
        'sudo mkdir ndb_data',
        'cd', #to move files from /home/ubuntu to /opt/mysqlcluster/deploy/conf
        'sudo cp config.ini my.cnf /opt/mysqlcluster/deploy/conf', #move files
        'sudo rm config.ini my.cnf', #remove files from home
        'cd /opt/mysqlcluster/home/mysqlc',
        'sudo scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data',
        'sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf > /dev/null 2>&1 &',
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(f'-------------- successfuly started the management node of mySQL cluster ---------------------------\n')  

    finally:
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly started the management node of mySQL cluster ---------------------------\n')  
        ssh_client.close()

def start_data_node(instance_id, key_file,mgmt_ip):
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        
        commands = [
            'sudo mkdir -p /opt/mysqlcluster/deploy/ndb_data',
            f'sudo /opt/mysqlcluster/home/mysqlc/bin/ndbd -c {mgmt_ip} > /dev/null 2>&1 &', 
            
            ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print('IT WORKED')
    finally:
        print(stdout.read().decode('utf-8'))
        ssh_client.close()

def start_mysql_server(instance_id, key_file):
    try:
        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)
        print('connected to instance via ssh')
        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            #create logfile
            'sudo touch /opt/mysqlcluster/home/mysqlc/bin/logfile.log',
            'sudo chmod 666 /opt/mysqlcluster/home/mysqlc/bin/logfile.log',

            #start 
            'sudo /opt/mysqlcluster/home/mysqlc/bin/mysqld --defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf --user=root > /opt/mysqlcluster/home/mysqlc/bin/logfile.log 2>&1 &', #start mysqld
            'sudo sleep 10',
            #decompress sakila database files
            'cd',
            'sudo tar -xvzf sakila-db.tar.gz',         

            #secure installation
            'cd /opt/mysqlcluster/home/mysqlc/bin',
            'echo -e "\nn\nn\nn\nY\nn\n" | mysql_secure_installation',
            
            #'echo "----------------------- installing sakila and creating user --------------------------------------"',
            #install sakila db
            'mysql -h 127.0.0.1 -u root -e "source /home/ubuntu/sakila-db/sakila-schema.sql; source /home/ubuntu/sakila-db/sakila-data.sql;" > /home/ubuntu/db_setup_schema.log 2>&1',
            
            #login in root, create user (local instance and also from anywhere (%)) and give rights, 
            "mysql -h 127.0.0.1 -u root -e \"USE sakila; CREATE USER 'simon'@'localhost' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'localhost' IDENTIFIED BY 'nomis'; CREATE USER 'simon'@'%' IDENTIFIED BY 'nomis'; GRANT ALL PRIVILEGES ON *.* TO 'simon'@'%' IDENTIFIED BY 'nomis'; FLUSH PRIVILEGES;\" > /home/ubuntu/db_setup.log 2>&1",
            
            #commands for installing and preparing sysbench
            'sudo apt-get install sysbench -y',
            'sudo sysbench --db-driver=mysql --mysql-user=root --mysql-db=sakila --table_size=10000 /usr/share/sysbench/oltp_read_only.lua prepare',
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
            if instance['State']['Name'] == 'running' and instance.get('InstanceType') == 't2.micro': 
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
 
    aws_access_key_id='ASIAQDC3YUDERRDKUAQD'
    aws_secret_access_key='8yx7uYSLkvJeZKk/W87A5nCVh+tQJ0dXAYQo3r/z'
    aws_session_token='FwoGZXIvYXdzEGIaDKna5Ls9r8jrMs70TCLIAcUZ+h9988BZvddMc+lQWmZCTka2MtXR1t089EyeYzLhqnlnOkfCIRWUwDKWez5k2yA9JSSE9Y6kn/NveUPY7cfF/vjxREWRzHzu/7k+ZuLi1PnfojvxkugrGM3qDrH7AoRudIlvcK7anPA/kDvFsOXw2z+MUBARO6wP97PDDfaXjjpUMXAU3pdomjFZqjzII5hPkBhnPyQ0FVmX71EAkKlyjoe0eW6NVI12Ls312af1nISF4Wka7okx1hDJoAenZhmartbtzTmDKPLBg6wGMi1GUpEnJb/JmKeb594BF7JPUS5JG1FdDaubAtwzkpcGi8pH76nmaO/nsKKoh10='
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

    mgmt_ip, data_nodes_ips, manag_public_ip = start_cluster_sql()

    output_dict = {
        "mgmt_ip": mgmt_ip,
        "data_nodes_ips": data_nodes_ips,
        "mgmt_public_ip": manag_public_ip
    }

    print(output_dict)
    # Write the dictionary to a JSON file
    with open('cluster_ips.json', 'w') as json_file:
        json.dump(output_dict, json_file)