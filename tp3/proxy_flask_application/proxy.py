from flask import Flask, request
import requests
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    return 'Hello, World! FROM PROXY '

if __name__ == '__main__':
    # Listen on port 80 for external traffic
    app.run(host='0.0.0.0', port=80, debug=True)

