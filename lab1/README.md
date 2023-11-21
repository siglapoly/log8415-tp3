# LAB 1 
# Make sure that python and pip are installed in your machine
To lunch the web app locally run :
- Open a command prompt in this directory
- run: python3 -m venv venv
- run : source venv/bin/activate (linux) or venv\Scripts\activate
- run : python -m pip install -r requirements.txt
- run : python main.py 
The app should be running in 127.0.0.1 port 4200. 



# To use the script in the Docker container :

First, the image must be created with the following command (this can take some time) : 

docker build -t python-analysis-script .

To execute the image : 

docker run python-analysis-script

# To use the script : 
- First, make sure that docker is installed and running in your local machine.
- Make sure that python and pip are installed in your machine.
- Make sure that the script has the execute permission set. If it doesn't, you can set it using the chmod command like this: chmod +x scripts.sh.
- To run the script, execute this command in your shell : ./scripts.sh. 
- A prompt will ask your aws credentials such as aws access key id, aws secret access key, aws session token and aws default region.  
- Once you provide your credentials, the pipeline will launch all the scripts. 

