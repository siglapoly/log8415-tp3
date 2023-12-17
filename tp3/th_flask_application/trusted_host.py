from flask import Flask, request

app = Flask(__name__)

allowed_ip = '172.31.6.237'

@app.route('/', methods=['GET', 'POST'])
def handle_request():
    return "Hello from Flask App 2!"

if __name__ == '__main__':
    # Listen on 443 port (HTTPS)
    app.run(host='0.0.0.0', port=443,debug=True)
