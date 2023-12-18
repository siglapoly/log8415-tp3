from flask import Flask, request
import requests
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def forward_request():
    if request.method == 'GET':
        # Forward GET request to mgmt_ip
        response = requests.get(f'http://172.31.9.122', headers=request.headers, data=request.get_data())
    elif request.method == 'POST':
        # Forward POST request to a randomly selected data node
        selected_ip = str(random.choice(f'['172.31.56.11', '172.31.39.116', '172.31.83.63']'))
        response = requests.post(http://selected_ip, headers=request.headers, data=request.get_data())
    else:
        # Handle other HTTP methods if needed
        response = None

    if response:
        # Return the response from the target server to the original requester
        return response.content, response.status_code, response.headers.items()
    else:
        return "Unsupported HTTP method", 400

if __name__ == '__main__':
    # Listen on port 80 for external traffic
    app.run(host='0.0.0.0', port=80, debug=True)

