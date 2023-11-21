import requests
import threading
import boto3
import sys


headers = {
    "Content-Type": "application/json", 
}

def consume_post_requests_sync(url, index):
    # specify the request wanted
    data_to_send = {"request": "run_model", "request_number": index}
    print(f"Sending request to {data_to_send['request_number']}")
    response = requests.post(url, json=data_to_send, headers=headers)
    response.raise_for_status()

    # Process the response data
    data = response.json()
    print(f"Response received: {data}")

def start_threads(url):
    # Creating threads and sending 15 requests to the orchestrator
    threads = []
    for i in range(15):
        threads.append(threading.Thread(target=consume_post_requests_sync, args=(url,i,))) 

    for thread in threads : 
        # Starting the threads
        thread.start()

    for thread in threads : 
        # waiting until the thread is finished
        thread.join()

# get instance information
def get_instance():
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['Placement']['AvailabilityZone'] == 'us-east-1a' and instance['State']['Name'] == 'running':
                return instance
            
    return False

if __name__ == "__main__" : 
    global ec2
    global aws_console

    print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
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

    # Get the public IP of the orchestrator 
    instance = get_instance()
    if instance :
        public_ip = instance.get('PublicIpAddress')
        url = f'http://{public_ip}:80/new_request'
        try:
            print('Now running threads to send requests')
            start_threads(url)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")