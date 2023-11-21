from flask import Flask, jsonify,request
import requests
import threading
import json
import time

app = Flask(__name__)
lock = threading.Lock()
request_queue = []


def send_request_to_container(container_id, container_info, incoming_request_data):
    try:
        # get the path request from the user
        req = incoming_request_data['request']
        # get the request number to print it 
        req_nb = incoming_request_data['request_number']
        # get the container IP 
        ip = container_info['ip']
        # get the container port
        port = container_info['port']
        
        print(f"Sending request to {container_id} with request: {req} and request nb : {req_nb} ")   
        # send post request to container     
        url = f"http://{ip}:{port}/{req}" 
        response = requests.post(url)
        # wait for reponse
        response.raise_for_status()

        print(f"request nb : {req_nb}.Received response from {container_id} and req : {req_nb} . {response.text} ")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


def update_container_status(container_id, status):
    with lock:
        with open("info.json", "r") as f : 
            data = json.load(f)
        data[container_id]["status"]= status
        with open("info.json", "w") as f : 
            json.dump(data,f) 

def process_request(incoming_request_data):
    with lock :
        with open("info.json", "r") as f : 
            data = json.load(f)
    free_container = None
    for container_id,container_info in data.items():
        if container_info["status"] == "free":
            free_container=container_id
            break
    if free_container:
        update_container_status(free_container, "busy")
        send_request_to_container(free_container, data[free_container], incoming_request_data)
        update_container_status(free_container, "free")
        # process the queued requests
        while request_queue:
            next_request_data = request_queue.pop(0)
            process_request(next_request_data)        
    else:
        # put the incomming rquest in queue
        request_queue.append(incoming_request_data)

# new request from client
@app.route('/new_request', methods=["POST"])
def new_request():
    incoming_request_data = request.json
    # create a thread to process the request
    threading.Thread(target=process_request, args=(incoming_request_data,)).start()
    # Send the client a response that says the request is beeing proccessed
    return jsonify({"message":f"request received {incoming_request_data} and processing started."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)