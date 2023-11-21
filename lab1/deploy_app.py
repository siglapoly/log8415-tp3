import boto3 
import os
import paramiko
import botocore
import sys
from botocore.exceptions import ClientError

def lunch_deploy():
    # get current path folder 
    current_directory = os.path.dirname(os.path.realpath(__file__))
    flask_app_directory = os.path.join(current_directory, 'flask_application')
    instance_ids , public_ip_addresses = get_instance()
    # deploy a simple flask app with ssh console
    for instance_id in instance_ids :        
        deploy_flask_app(instance_id, 'bot.pem', flask_app_directory)
    
    # diplays the http app link 
    display_app_link(public_ip_addresses)    

# function to deploy a flask application via SSH  
# (Parameter) (string) instance_id : The id of the instance to lunch the app . 
# (Parameter) (string) key_file : The path to the pem key associated with instance
# (Parameter) (string) flask_app_directory : The path to the flask_app directory

def deploy_flask_app(instance_id, key_file, flask_app_directory):
    try:
        create_app_file(instance_id, flask_app_directory)

        # Get the public IP address of the instance
        response = ec2.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r {flask_app_directory} ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying local Flask app code to {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Command to run the flask app in the instance
        commands = [
            'echo "----------------------- instaling packages ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'sudo apt install python3-venv -y',
            'cd flask_application',
            'sudo python3 -m venv venv',
            'echo "----------------------- activate venv environment ------------------------------"',
            'source venv/bin/activate',
            'sudo pip install Flask',
            'export flask_application=main.py',
            'echo "----------------------- lunching flask app --------------------------------------"',
            'nohup sudo python3 main.py > /dev/null 2>&1 &'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)       
                
    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfuly deployed in http://{public_ip}:80 ---------------------------\n')  
        os.system('rm flask_application/main.py')
        ssh_client.close()


# function to create main.py file to lunch application on port 80   
# (Parameter) (string) instance_id : The id of the instance to lunch the app . 
# (Parameter) (string) flask_app_directory : The path to the flask_app directory

def create_app_file(instance_id, flask_app_directory) : 
    create_file = f'''cat <<EOF > {flask_app_directory}/main.py
# importing flask framework 
from flask import Flask

app = Flask(__name__)
# root redirection to the hello world page
@app.route('/')
def hello():
    return '<h1>this is instance {instance_id} </h1>'
# /about redirection to another page 
@app.route('/about/')
def about():
    return '<h3>This is a Flask web application.</h3>'
# /cluster1 redirection to another page 
@app.route('/cluster1/')
def cluster1():
    return '<h3>This is the cluster1 page of instance {instance_id} .</h3>'
# /cluster2 redirection to another page 
@app.route('/cluster2/')
def cluster2():
    return '<h3>This is the cluster2 page of instance {instance_id} .</h3>'
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
EOF'''     
    os.system(create_file)


# function to get all instances IDS 
# return a list of all the instances IDS 
def display_app_link(public_ip_addresses):
    # Print the list of public IP addresses
    for ip in public_ip_addresses:
        print(f'A flask_app will be deployed in http://{ip}:80')
    print('\n')

def get_instance():
    # Extract public IP addresses from the response
    public_ip_addresses = []
    instance_id_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')

                instance_id_list.append(instance_id)
                if public_ip:
                    public_ip_addresses.append(public_ip)
            
    return instance_id_list , public_ip_addresses


if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script deploys a simple flask application in each EC2 instance on port 80 \n")          
    
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
    lunch_deploy()