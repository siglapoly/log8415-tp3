from flask import Flask, request
import requests

app = Flask(__name__)

th_url = 'http://ip-172-31-91-164.ec2.internal:443'

@app.route('/', methods=['GET', 'POST'])
def forward_request():

    # Forward the incoming request to trusted host only if ip of request is trusted
    client_ip = request.remote_addr
    if client_ip in ['24.202.63.137']:
        response = requests.request(request.method, th_url + request.path, headers=request.headers, data=request.get_data())
    
        # Return the response from Flask App 2 to the original requester
        return response.content, response.status_code, response.headers.items()
    else:
        return "Unauthorized", 401

if __name__ == '__main__':
    # Listen on port 80 for external traffic
    app.run(host='0.0.0.0', port=80,debug=True)
