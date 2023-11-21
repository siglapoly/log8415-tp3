import requests
import time
import threading
import boto3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import os

ec2 = boto3.client('ec2')
cli = boto3.client('elbv2')
client = boto3.client('cloudwatch')
load_balancer_name = 'load-balancer-flask-app'


def consume_get_requests_sync(url):
    request = requests.get(url)

def scenario_1(url):
    # Scenario 1 : 1000 GET requests sequentially
    for x in range(1000):
        consume_get_requests_sync(url)

def scenario_2(url):
    # Scenario 2 : 500 GET requests, then one minute sleep, followed by 1000 GET requests
    for x in range(500):
        consume_get_requests_sync(url)

    # We wait one minute before continuing the get requests
    time.sleep(60)

    for x in range(1000):
        consume_get_requests_sync(url)


def get_stats(load_balancer_arn, pdf_document, metric, dimension_name, target_group_arn=None):
    stats_type = ['Sum', 'Minimum', 'Maximum', 'Average']

    if target_group_arn is None:
        dimensions = [
            {
                "Name": dimension_name,
                "Value": load_balancer_arn
            },
        ]
    else:
        dimensions = [
            {
                'Name': 'LoadBalancer',
                'Value': load_balancer_arn
            },
            {
                'Name': 'TargetGroup',
                'Value': target_group_arn
            }
        ]

    stats_value = []
    for stat_type in stats_type:
        # Get the stat for the metric in the last 60 minutes
        response = client.get_metric_statistics(
                Namespace="AWS/ApplicationELB",
                MetricName=metric,
                Dimensions=dimensions,
                StartTime=datetime.utcnow() - timedelta(minutes=60),  # data for the last 60 minutes
                EndTime=datetime.utcnow(),
                Period=3600,  
                Statistics=[
                    stat_type,
                ]
        )  

        if len(response['Datapoints']) > 0:
            stats_value.append(response['Datapoints'][0][stat_type])
        else:
            stats_value.append(0.0)
    
    # Create a DataFrame from the stats
    df = pd.DataFrame({'stat' : stats_type, 'value': stats_value})
    
    # Create a table from the DataFrame using matplotlib
    fig, ax = plt.subplots(1, 1)
    ax.axis('tight')
    ax.axis('off')
    ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    plt.title(f'Stats for the {metric} of the {dimension_name}')

    # Save the table as an image
    table_image = 'table.png'
    plt.savefig(table_image, format='png', bbox_inches='tight', pad_inches=0.1)
    plt.close()

    # Add the table image to the pdf output
    pdf_document.savefig(fig)

    # Delete the image
    if os.path.exists('table.png'):
        os.remove('table.png')


def get_metric_utilization_instance(metric, pdf_document):
    # Use the describe_instances() method to list all instances
    response = ec2.describe_instances()

    # Retrieve the metric utilization for every instance
    namespace = 'AWS/EC2'
    metric_name = metric 

    # Data from the last 60 minutes
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=60)

    # Data in interval of 1 minute
    period = 60  # 1 minute

    # Create a figure for the graph
    plt.figure()

    # Iterate through reservations and instances
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Check if the instance state is "running"
            if instance['State']['Name'] == 'running':
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']

                dimensions = [{'Name': 'InstanceId', 'Value': instance_id}] 

                # Retrieve metric data
                response = client.get_metric_data(
                    MetricDataQueries=[
                        {
                            'Id': 'm1',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': namespace,
                                    'MetricName': metric_name,
                                    'Dimensions': dimensions
                                },
                                'Period': period,
                                'Stat': 'Average',
                            },
                            'ReturnData': True,
                        },
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                )

                # Get the timestamp and values from the response
                timestamps = response['MetricDataResults'][0]['Timestamps']
                values = response['MetricDataResults'][0]['Values']

                # Choose color based on instance type
                if instance_type == 'm4.large':
                    color = 'red'
                else:
                    color = 'blue'

                # Add a line to the graph for every instance
                plt.plot(timestamps, values, marker='o', linestyle='-', label=f'{instance_id} - {instance_type}', color=color)


    # Add title, labels and legend to the graph
    plt.title(f'{metric_name} for instances')
    plt.xlabel('Timestamp')
    plt.ylabel(metric_name)
    plt.grid(True)
    plt.legend(loc='upper left', bbox_to_anchor=(0.5, 1))

    # Add the graph to the PDF document
    pdf_document.savefig()

    plt.close()


def get_metrics(metric, pdf_document, dimension_name, load_balancer_arn, target_group_arn=None):
    # Data from the last 60 minutes
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=60)

    # Data in interval of 1 minute
    period = 60  # 1 minute

    # Create a figure for the graph
    plt.figure()

    if target_group_arn is None:
        dimensions = [
            {
                'Name': dimension_name,
                'Value': load_balancer_arn
            }
        ]
    else:
        dimensions = [
            {
                'Name': 'LoadBalancer',
                'Value': load_balancer_arn
            },
            {
                'Name': 'TargetGroup',
                'Value': target_group_arn
            }
        ]

    # Retrieve metric data
    response = client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/ApplicationELB',
                        'MetricName': metric,
                        'Dimensions': dimensions
                    },
                    'Period': period,
                    'Stat': 'Average',
                },
                'ReturnData': True,
            },
        ],
        StartTime=start_time,
        EndTime=end_time,
    )

    # Get the timestamp and values from the response
    timestamps = response['MetricDataResults'][0]['Timestamps']
    values = response['MetricDataResults'][0]['Values']

    # Add a line to the graph for every instance
    plt.plot(timestamps, values, marker='o', linestyle='-')


    # Add title, labels and legend to the graph
    plt.title(f'{metric} for {dimension_name}')
    plt.xlabel('Timestamp')
    plt.ylabel(metric)
    plt.grid(True)

    # Add the graph to the PDF document
    pdf_document.savefig()

    plt.close()


def print_results_metrics_load_balancer_stats():
    # Create a PDF document for output to save the tables of the stats for the load balancer
    pdf_document = PdfPages('load_balancer_stats.pdf')

    # Get the ARN of the load balancer with its name
    response = cli.describe_load_balancers(
        Names=[load_balancer_name]
    )
    load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']

    # Find the index of 'app/' in the ARN
    start_index = load_balancer_arn.find('app/')

    if start_index != -1:
        # Extract the needed portion of the ARN starting from 'app/' till the end
        load_balancer_arn = load_balancer_arn[start_index:]

        metrics_stats_list = ['RequestCount', 'NewConnectionCount', 'ProcessedBytes']

        # Produce an output document with the tables for all the metrics of the load balancer
        for metric in metrics_stats_list:
            get_stats(load_balancer_arn, pdf_document, metric, 'LoadBalancer')


    # Close the PDF document
    pdf_document.close()


def print_results_metrics_targets_stats(group_name):
    # Create a PDF document for output to save the tables of the stats for the target groups
    pdf_document = PdfPages(f'target_stats_{group_name}.pdf')

    # Get the ARN of the load balancer with its name
    response = cli.describe_load_balancers(
        Names=[load_balancer_name]
    )
    load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']

    # Find the index of 'app/' in the ARN
    start_index_load_balancer = load_balancer_arn.find('app/')

    # Get the ARN of the target group with its name
    response = cli.describe_target_groups(
        Names=[group_name]
    )
    target_group_arn = response['TargetGroups'][0]['TargetGroupArn']

    # Find the index of 'targetgroup/' in the ARN
    start_index_target_group = target_group_arn.find('targetgroup/')

    if start_index_load_balancer != -1 and start_index_target_group != -1:
        # Extract the needed portion of the ARN starting from 'app/' till the end
        load_balancer_arn = load_balancer_arn[start_index_load_balancer:]

        # Extract the needed portion of the ARN starting from 'targetgroup/' till the end
        target_group_arn = target_group_arn[start_index_target_group:]

        metrics_stats_list = ['RequestCount', 'HealthyHostCount', 'RequestCountPerTarget', 'TargetResponseTime', 'UnHealthyHostCount']

        # Produce an output document with the tables for all the metrics of the target groups
        for metric in metrics_stats_list:
            get_stats(load_balancer_arn, pdf_document, metric, 'TargetGroup', target_group_arn)


    # Close the PDF document
    pdf_document.close()


def print_results_metrics_load_balancer():
    # Create a PDF document for output to save the graphs
    pdf_document = PdfPages('load_balancer_metric_graphs.pdf')

    # Get the ARN of the load balancer with its name
    response = cli.describe_load_balancers(
        Names=[load_balancer_name]
    )
    load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']

    # Find the index of 'app/' in the ARN
    start_index = load_balancer_arn.find('app/')

    if start_index != -1:
        # Extract the needed portion of the ARN starting from 'app/' till the end
        load_balancer_arn = load_balancer_arn[start_index:]

        metrics_instance_list = ['RequestCount', 'NewConnectionCount', 'ProcessedBytes']

        # Produce an output document with the graphs for all the metrics of the load balancer
        for metric in metrics_instance_list:
            get_metrics(metric, pdf_document, 'LoadBalancer', load_balancer_arn)


    # Close the PDF document
    pdf_document.close()


def print_results_metrics_target_group(group_name):
    # Create a PDF document for output to save the graphs
    pdf_document = PdfPages(f'target_group_metric_graphs_{group_name}.pdf')
    
    # Get the ARN of the load balancer with its name
    response = cli.describe_load_balancers(
        Names=[load_balancer_name]
    )
    load_balancer_arn = response['LoadBalancers'][0]['LoadBalancerArn']

    # Get the ARN of the target group with its name
    response = cli.describe_target_groups(
        Names=[group_name]
    )
    target_group_arn = response['TargetGroups'][0]['TargetGroupArn']

    # Find the index of 'app/' in the ARN for the load balancer
    start_index_load_balancer = load_balancer_arn.find('app/')

    # Find the index of 'targetgroup/' in the ARN for the target group
    start_index_target_group = target_group_arn.find('targetgroup/')

    if start_index_load_balancer != -1 and start_index_target_group != -1:
        # Extract the needed portion of the ARN starting from 'app/' till the end
        load_balancer_arn = load_balancer_arn[start_index_load_balancer:]

        # Extract the needed portion of the ARN starting from 'targetgroup/' till the end
        target_group_arn = target_group_arn[start_index_target_group:]

        metrics_instance_list = ['RequestCount', 'HealthyHostCount', 'RequestCountPerTarget', 'TargetResponseTime', 'UnHealthyHostCount']

        # Produce an output document with the graphs for all the metrics of the target group
        for metric in metrics_instance_list:
            get_metrics(metric, pdf_document, 'TargetGroup', load_balancer_arn, target_group_arn)


    # Close the PDF document
    pdf_document.close()


def print_results_metrics_utilization_instances():
    # Create a PDF document for output to save the graphs
    pdf_document = PdfPages('instances_metric_graphs.pdf')

    metrics_instance_list = ['CPUUtilization', 'NetworkIn', 'NetworkOut']

    # Produce an output document with the graphs for all the metrics of every instance
    for metric in metrics_instance_list:
        get_metric_utilization_instance(metric, pdf_document)

    # Close the PDF document
    pdf_document.close()


def start_threads(url):
    # Creating threads for the first and second scenarios
    thread_1 = threading.Thread(target=scenario_1, args=(url,))
    thread_2 = threading.Thread(target=scenario_2, args=(url,))

    # Starting the thread for the first scenario
    thread_1.start()
    # Starting the thread for the second scenario
    thread_2.start()

    # Wait until the first thread is completely executed
    thread_1.join()
    # Wait until the second thread is completely executed
    thread_2.join()


if __name__ == "__main__" :  
    # Get the URL of the load balancer with its name to send requests to it
    response = cli.describe_load_balancers(
        Names=[load_balancer_name]
    )
    load_balancer_url = response['LoadBalancers'][0]['DNSName']
    
    print('Now running threads for cluster1.')
    # Run both threads for cluster1
    url = f'http://{load_balancer_url}/cluster1'
    start_threads(url)

    print('Now running threads for cluster2.')
    # Run both threads for cluster2
    url = f'http://{load_balancer_url}/cluster2'
    start_threads(url)

    # Show the results 
    print('Starting to output the results...')
    # We wait two minutes before fetching the results to make sure the data has been updated
    time.sleep(120)
    print('Printing the tables with the load balancer statistics.')
    print_results_metrics_load_balancer_stats()
    print('Printing the tables with the target group groupM4 statistics.')
    print_results_metrics_targets_stats('groupM4')
    print('Printing the tables with the target group groupT2 statistics.')
    print_results_metrics_targets_stats('groupT2')
    print('Printing the graphs for the load balancer metrics.')
    print_results_metrics_load_balancer()
    print('Printing the graphs for the target group groupM4 metrics.')
    print_results_metrics_target_group('groupM4')
    print('Printing the graphs for the target group groupT2 metrics.')
    print_results_metrics_target_group('groupT2')
    print('Printing the graphs for the resources utilization of the instances.')
    print_results_metrics_utilization_instances()
    print('All results have been printed. See the pdfs output in current directory for graphs and tables.')