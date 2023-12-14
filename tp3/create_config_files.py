import boto3 
import os
import botocore
import platform
import subprocess
import sys
from botocore.exceptions import ClientError

def create_config_file():
    instance_infos = get_instance_infos()

    #management node
    instance_id, internal_ip = instance_infos[1]
    cluster_management_ip = internal_ip
    cluster_management_ip = 'ip-'  + cluster_management_ip.replace('.','-') + '.ec2.internal' 

    #data nodes
    cluster_workers_ip = []
    for instance in instance_infos[2:5]:
        instance_id, internal_ip = instance
        cluster_workers_ip.append(internal_ip)
    cluster_workers_ip = ['ip-'  + x.replace('.','-') + '.ec2.internal' for x in cluster_workers_ip]

    config_content = f"""[ndb_mgmd]
hostname={cluster_management_ip}
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas={len(cluster_workers_ip)}
datadir=/opt/mysqlcluster/deploy/ndb_data
Serverport=2200
"""

    # Add ndbd entries
    for i, ndbd_hostname in enumerate(cluster_workers_ip, start=3):
        config_content += f"\n[ndbd]\nhostname={ndbd_hostname}\nnodeid={i}\n"

    # Add mysqld entry
    config_content += "\n[mysqld]\nnodeid=50\n"

    config_file_path = 'config.ini'
    # Write the configuration to the file
    with open(config_file_path, 'w') as config_file:
        config_file.write(config_content)
       
    # function to give read only permission
    set_file_permissions('config.ini')
    set_file_permissions('my.cnf')

def set_file_permissions(file_path):

    # read only permissions on windows 
    if platform.system() == 'Windows':
        try:
            subprocess.run(["icacls", file_path, "/inheritance:r", "/grant:r", f"*S-1-5-32-545:(R)"])
        except Exception as e:
            print(f"Failed to set permissions on Windows: {e}")
    else:
        try:
            # Set the file permissions to chmod 400
            os.chmod(file_path, 0o400)
        except Exception as e:
            print(f"Failed to set permissions on Unix-like system: {e}")

def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':# and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                internal_ip = instance.get('PrivateIpAddress')
                instance_id_list.append((instance_id,internal_ip))
    return instance_id_list
if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script creates the needed config file (config.ini) based on cluster instances ips\n")          
    
    #print("This script creates the config.ini file based on ips
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDEVSWB2EPP'
    aws_secret_access_key='/2wIUiTYrkB0689ozd757fP65ucbRCV/N4DqJjHN'
    aws_session_token='FwoGZXIvYXdzEPz//////////wEaDMnl3VHBT2nPsDlDZiLIAa2XVfwcmbGqpjV7ly6oluol+tC+O6RuH2CRQqxdubczWVi6DbJ6ELOWKfLxCEHGxG83o54oE4l0OZzQ7XID76AL3l+h45SEWZj36RGz+ySY7cWXRI2HGFj9PMdAwFRluwBUqYWCfx0HdLsBXAGHTItectvIrJkLiCk9WEPImHTDvEpN7+SwsS3/eUIcM0VfuuwjvWw8Cy0tEKK3d1UYErcdQ8wCW1y8vjts3NhQqXOFKDdHkj6LKYhdLCJZYE1wYw7lLoJfnTucKMGV7asGMi3Ededr3OvOVroFmc1E26hf/2ER4vuXrPFMNSSC/bMDzN2+ketZX8nE7yAZ3Uw='
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

    create_config_file()