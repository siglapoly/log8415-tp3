import boto3 
import os
import botocore
import platform
import subprocess
import sys
from botocore.exceptions import ClientError


#commands to run on all cluster instances (manager and worker nodes)
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
    'sudo apt-get update && sudo apt-get -y install libncurses5',

]

#commands to run on the management node 

commands = [
    'sudo mkdir -p /opt/mysqlcluster/deploy',
    'cd /opt/mysqlcluster/deploy',
    'sudo mkdir conf',
    'sudo mkdir mysqld_data',
    'sudo mkdir ndb_data',
    'cd conf',






]