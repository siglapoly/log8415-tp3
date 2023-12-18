from flask import Flask, request
import requests
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def forward_request():
    if request.method == 'POST':
        # Forward GET request to mgmt_ip
        response = requests.get(f'http://172.31.15.5', headers=request.headers, data=request.get_data())
    elif request.method == 'GET':
        # Forward POST request to a randomly selected data node
        selected_ip = 'http://' + str(random.choice(['172.31.61.27', '172.31.88.175', '172.31.21.85']))
        response = requests.post(selected_ip, headers=request.headers, data=request.get_data())
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

