import boto3 
import os
import botocore
import platform
import subprocess
import sys
import time 
import paramiko
from botocore.exceptions import ClientError

def launch_gatekeeper():
    pass




def get_instance_infos():    
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running': 
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
 
    aws_access_key_id='ASIAQDC3YUDEVRA52Z7L'
    aws_secret_access_key='9DcJmJ/2iC4QzqekqdU2MpqINhp46cqXmhKgJPif'
    aws_session_token='FwoGZXIvYXdzEAIaDKQIaKCh9SPSDLmSMiLIATXSLTQYMHS6hIiiMtStdv7Vh0QptJCAUmSkaJ4m3pyo0Lcn/J1PmnvsHv13PGYnBtstyCe4Krh0hQG6WO+E12lxl4oDu7BjD0PZVGwpj3ig/fV4Z3TuXzJ+Gb06ffDCbOQgnlCM0kw7kDjmmXDjj/nsPIqlHxC01x+C1iU7GBNE5aTnUiU7x/JsiSIFWvEsGaeFp7kwQV5CzE6wtVPFPmTqDpcyMkckzhd0f0a8WSXabionb7F7zCmryRGwbfd5ZdSTvFy1KIfXKLu/7qsGMi02LM/XX8MF1jYiVANJi12ECUAdBSqo3DsNVzWJvuNOyzMbjMUNzkVRO00SxHI='
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
    launch_gatekeeper()


