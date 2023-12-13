import boto3 
import os
import botocore
import platform
import subprocess
import sys
from botocore.exceptions import ClientError

def create_config_file():
    instance_id_list, cluster_management_ip, cluster_workers_ip = get_instance_infos()

    cluster_management_ip = 'ip-'  + cluster_management_ip[0].replace('.','-') + '.ec2.internal' ###WHY WE NEED THE REPLACE ? #prbl not getting good ip from instance
    
    cluster_workers_ip = ['ip-'  + x.replace('.','-') + '.ec2.internal' for x in cluster_workers_ip]
    print(cluster_workers_ip)

    config_content = f"""[ndb_mgmd]
hostname={cluster_management_ip}
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas={len(cluster_workers_ip)}
datadir=/opt/mysqlcluster/deploy/ndb_data
Serverport=2202
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


# Example usage
# mgmd_hostname = 'domU-12-31-39-04-D6-A3.compute-1.internal'
# ndbd_hostnames = ['ip-10-72-50-247.ec2.internal', 'ip-10-194-139-246.ec2.internal']

# create_config_file('config.ini', mgmd_hostname, ndbd_hostnames)
# print("Configuration file 'config.ini' created successfully.")



def get_instance_infos():    
    instance_id_list = []
    cluster_management_ip = []
    cluster_workers_ip = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance in zone us-east-1a is the standalone_sql 
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
                internal_ip = instance.get('PrivateIpAddress')
                instance_id_list.append((instance_id,public_ip))

                if instance['Placement']['AvailabilityZone'] == 'us-east-1b':
                    cluster_management_ip.append(internal_ip)
                else:
                    cluster_workers_ip.append(internal_ip)
    return instance_id_list, cluster_management_ip, cluster_workers_ip

if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script creates the needed config file (config.ini) based on cluster instances ips\n")          
    
    #print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
    #if len(sys.argv) != 5:
    #    print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
    #    sys.exit(1)
 
    aws_access_key_id='ASIAQDC3YUDEY6WMNM7D'
    aws_secret_access_key='/7plkDjzFAJZO1Tc5Tuipz3/gl2XXKpXA/6Jy3+o'
    aws_session_token='FwoGZXIvYXdzENP//////////wEaDLsLPcGdwDeJjFByJiLIAYn5zR8GtRpu5BcxwUPi/Sgu7K+983tncxrsYGkR47b2XRluUU7//QujI2Fd9eXmN2KHtVROPlJkkVJNll4qSzOQECXIclmDT2BsiHxEW6/l/MlP2MG0QoFJ0pF8ZWddl5HMfw5Z+b5AsZ1pmQsPuU94KBIqtPdo9qb4ve88w3gV/p6TccAvzgErf9XdvojKYlX9JId/l98+euRsVKI2YT8pVvrfYUjCt5N9/lMyG3v9Tv0cbUnW1DyrKBhYfkfOyfNr8tx++C1LKJaS5KsGMi1fhPRhrphE6kIQcSajgd3vWtCHKA8+KcXSs5nxIqlHCNd3CjCLuBTtjdj/Oxk='
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