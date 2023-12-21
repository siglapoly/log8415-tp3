from flask import Flask, request
import requests

app = Flask(__name__)

proxy_url = 'http://ip-172-31-16-193.ec2.internal:443'

@app.route('/', methods=['GET', 'POST'])
def forward_request():

    # Forward the incoming request to the proxy

    response = requests.request(request.method, proxy_url + request.path, headers=request.headers, data=request.get_data())

    # Return the response from proxy to the original requester
    return response.content, response.status_code, response.headers.items()

if __name__ == '__main__':
    # Listen on port 80 for external traffic
    app.run(host='0.0.0.0', port=80,debug=True)
