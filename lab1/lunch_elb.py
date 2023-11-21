import boto3 
import sys

def launch_elastic_load_balancer():
    # Get all the instances
    subnets_with_active_instances, instances_m4, instances_t2, vpc_id = get_instances()

    # Create the load balancer
    response_lb_arn = create_elastic_load_balancer(subnets_with_active_instances)

    # Create the target groups for m4.large and t2.large instances and register targets
    response_tg_arn_m4 = create_target_group('groupM4', vpc_id, instances_m4)
    response_tg_arn_t2 = create_target_group('groupT2', vpc_id, instances_t2)

    # Create a listener for port 80 HTTP
    response_li_arn = create_listener(response_lb_arn, response_tg_arn_m4)
    
    # Create rules for the listener for each cluster route
    create_rule(response_li_arn, response_tg_arn_m4, '/cluster1', 1)
    create_rule(response_li_arn, response_tg_arn_t2, '/cluster2', 2)


def get_instances():
    # Use the describe_instances() method to list all instances
    response = ec2.describe_instances()

    # Create a set to store the subnet IDs and instances ids 
    subnets_with_active_instances = set()
    instances_m4 = set()
    instances_t2 = set()

    # Iterate through reservations and instances
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Check if the instance state is "running"
            if instance['State']['Name'] == 'running':
                # Add the subnet ID to the set
                subnets_with_active_instances.add(instance['SubnetId'])
                # Check if the instance type is "m4.large"
                if instance['InstanceType'] == 'm4.large':
                    instances_m4.add(instance['InstanceId'])
                # Check if the instance type is "t2.large"
                if instance['InstanceType'] == 't2.large':
                    instances_t2.add(instance['InstanceId'])
                vpc_id = instance['VpcId'] #keep one vpc id from the instances, should be the same for all instances


    #change subnets ids and instances ids to lists
    subnets_with_active_instances = list(subnets_with_active_instances)
    instances_m4 = list(instances_m4)
    instances_t2 = list(instances_t2)

    #create dict for instances ids
    #we want instances in the format dict : {Id : idXASDASDA}for value in instances_m4]
    instances_m4_ids = [{'Id':value} for value in instances_m4]
    instances_t2_ids = [{'Id':value} for value in instances_t2]

    return subnets_with_active_instances, instances_m4_ids, instances_t2_ids, vpc_id


def create_elastic_load_balancer(subnets_with_active_instances):
    # Get the security group id with the security group name
    response = ec2.describe_security_groups(
        GroupNames=['botSecurityGroup']
    )
    security_group_id = response['SecurityGroups'][0]['GroupId']

    #Create LoadBalancer
    response_lb = cli.create_load_balancer(
        Name='load-balancer-flask-app',
        Subnets=subnets_with_active_instances,
        SecurityGroups=[
            security_group_id,
        ],
        Type='application'
    )

    #Return the ARN of the load balancer, with the following format:
    #arn:aws:elasticloadbalancing:your_region:your_account_id:loadbalancer/load_balancer_name
    return response_lb['LoadBalancers'][0]['LoadBalancerArn']


def create_target_group(group_name, vpc_id, instances_ids):
    #create target groups 
    response_tg = cli.create_target_group(
        Name=group_name,
        Protocol='HTTP',
        Port=80,
        VpcId=vpc_id,
        IpAddressType='ipv4'   
    )
    
    #register targets
    cli.register_targets(
        TargetGroupArn=response_tg['TargetGroups'][0]['TargetGroupArn'], #Arn from previous response
        Targets=instances_ids #we want instances in the format dict : {Id : idXASDASDA}
    )

    #Return the ARN of the target group, with the following format:
    #arn:aws:elasticloadbalancing:your_region:your_account_id:targetgroup/target_group_name
    return response_tg['TargetGroups'][0]['TargetGroupArn']


def create_listener(response_lb_arn, response_tg_arn):
    #create listener for port 80 HTTP
    response_li = cli.create_listener( 
        LoadBalancerArn=response_lb_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[ #when a request does not match any of the defined listener rules, send a predefined response
        {
            'Type': 'forward',
            'TargetGroupArn': response_tg_arn
        }
        ],
    )

    #Return the ARN of the listener, with the following format:
    #arn:aws:elasticloadbalancing:your_region:your_account_id:listener/listener_id
    return response_li['Listeners'][0]['ListenerArn']


def create_rule(response_li_arn, response_tg_arn, route, priority):
    # Create a rule for the cluster route that forward requests to the target group
    # and associate it with the listener
    response_ru = cli.create_rule(
        ListenerArn=response_li_arn,
        Conditions=[
            {
                'Field': 'path-pattern',
                'Values': [route]
            }
        ],
        Priority=priority,
        Actions=[
            {
                'Type': 'forward',
                'TargetGroupArn': response_tg_arn
            }
        ]
    )

if __name__ == '__main__':

    global ec2
    global aws_console
    global cli

    print("This script lunchs an elastic load balancer \n")          
    
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
    # Client for load balancer
    cli = aws_console.client('elbv2')

    launch_elastic_load_balancer()



