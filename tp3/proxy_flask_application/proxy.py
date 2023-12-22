from flask import Flask, request
import mysql.connector
import random

app = Flask(__name__)

# Replace these with your actual MySQL Cluster connection details
mysql_config = dict(
    #host= 'ip-172-31-63-209.ec2.internal',
    user= 'simon',
    password= 'nomis',
    database= 'sakila',  
)

@app.route('/', methods=['GET', 'POST'])
def forward_request():
    sql_query = request.get_data(as_text=True)#.upper()

    if 'SELECT' in sql_query:
        responding_instance, result = handle_read_request(sql_query)
        print('SELECT QUERY')
    else:
        responding_instance, result = handle_write_request(sql_query)
        print('WRITE QUERY')

    print("Responding instance: + str(responding_instance)")
    print("Query result: + str(result)")

    return "Request handled", 200

def handle_read_request(sql_query):
    selected_ip = random.choice(['172.31.87.193', '172.31.19.35', '172.31.9.115'])
    result = execute_sql_query(sql_query, selected_ip)
    return selected_ip, result

def handle_write_request(sql_query):
    result = execute_sql_query(sql_query, '172.31.63.209')
    return mgmt_ip, result

def execute_sql_query(sql_query, host):
    connection = mysql.connector.connect(**mysql_config, host=host)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql_query)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return result

if __name__ == '__main__':
    # Listen on port 443 for internal traffic
    app.run(host='0.0.0.0', port=443, debug=True)
