import boto3 
import os
import botocore
import platform
import subprocess
import sys
from botocore.exceptions import ClientError

# create and deploy a flask app on lunching 
def lunch_ec2(): 
    # create SSH key_pair named 'bot.pem' 
    keypair_name = create_key_pair()

    # create security group named 'botSecurityGroup' that allows SHH and http trafic 
    security_group_id = create_security_group()
 
    # lunch instances 5 of type m4.large and 4 of type t2.large 
    m4_instance_ids = create_instances('m4.large',keypair_name,[security_group_id], ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e'])
    t2_instance_ids = create_instances('t2.large',keypair_name,[security_group_id], ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d'])

    print('m4.large instance ids : ', m4_instance_ids)
    print('t2.large instance ids : ', t2_instance_ids)


# function that creates and saves an ssh key pair. It also gives read only permission to the file  
def create_key_pair():
    key_pair_name = 'bot'
    try:
        keypair = ec2.create_key_pair(KeyName='bot', KeyFormat='pem', KeyType='rsa')
        current_directory = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(current_directory, f'{key_pair_name}.pem')
        
        # save key_pair
        with open(f'{key_pair_name}.pem', 'w') as key_file:
            key_file.write(keypair['KeyMaterial'])
        
        # function to give read only permission
        set_file_permissions(file_path)
        
        print(f"Key pair '{key_pair_name}' created successfully and saved")
        return key_pair_name
    except ec2.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            return key_pair_name
        else:
            raise 

# function to give read only permission
# (parameter) (string) file_path : path to the file
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


# function to create a security group that allows HTTP trafic on port 80 
def create_security_group():

    try:
        # Create a security group allowing HTTP (port 80), HTTPS (port 443) and shh (port 22) traffic
        response = ec2.create_security_group(
            Description='This security group is for the bot',
            GroupName='botSecurityGroup',
        )
        security_group_id = response['GroupId']

        # Authorize inbound traffic for HTTP (port 80) 
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for HTTPS (port 443)
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=443,
            ToPort=443,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for ssh (port 22)
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [
                        {
                            'CidrIp': '0.0.0.0/0',  # Open to all traffic 
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
                'Values': ['botSecurityGroup']
                    }
                ]
            )
            return response['SecurityGroups'][0]['GroupId']
        else:
            print(f"Failed to create security group {e}")


# function to lunch instances with a specific type in multiple availability zones
# (Parameter) (string) instance_type : the type of the instance . Example : 'm4.large'
# (Parameter) (string) keypair_name : The name of the key pair.
# (Parameter) (list of string) security_group_id : The security group ids.
# (Parameter) (list of string) availability_zones : the zones that hosts the EC2 instances
# (return) list of string that contains the instance ids 

def create_instances(instance_type, keypair_name, security_group_id, availability_zones):
    # Machine Image Id. We use : Ubuntu, 22.04 LTS. Id found in aws console  
    image_id = "ami-053b0d53c279acc90"
    instance_ids = []
    response = {}
    try:
        # Launch instances in each availability zone
        for az in availability_zones:
            response = ec2.run_instances(
                ImageId=image_id,  
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=security_group_id,
                KeyName=keypair_name,
                Placement={'AvailabilityZone': az}
                )
            # Get the instance ID
            instance_id = response['Instances'][0]['InstanceId']

            # wait to create the instance
            ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
            instance_ids.append(instance_id)
            print(f'Launched instance {instance_id} in availability zone {az}')

        
        print(f'all {instance_type} instances are created successfully')       
        return instance_ids 

    except ClientError as e:
        return []
        print(e.response['Error']['Message'])
        
if __name__ == '__main__':
    global ec2
    global aws_console

    print("This script launchs overall 10 EC2 instances (5 of type M4.Large and 4 of typeT2.Large) in different Availability Zones.\n")          
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
    lunch_ec2()





