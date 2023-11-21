from flask import Flask, jsonify, render_template_string
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import torch
import random
import string

pretrained_source = 'distilbert-base-uncased'

tokenizer = DistilBertTokenizer.from_pretrained(pretrained_source)
model = DistilBertForSequenceClassification.from_pretrained(pretrained_source)

app = Flask(__name__)

def generate_random_text(length=50):
    '''
    Function to generate random sentence to feed the model
    Parameters
    ----------
    length : int, optional
        The number of letters to be used (total) for the random sentence generation

    Returns
    -------
    Random sentence. (str)
    
    '''
    letters = string.ascii_lowercase + ' '
    return (''.join(random.choice(letters) for i in range(length)))

# root redirection to the hello world page
@app.route('/')
def hello():
    return '<h1>Hello from instance worker </h1>'

# /about redirection to another page 
@app.route('/about/')
def about():
    return '<h3>This is a Flask web application.</h3>'

#model redirection
@app.route('/run_model', methods=["POST"])
def run_model():
    input_text = generate_random_text()
    inputs = tokenizer(input_text,return_tensors='pt',padding=True,truncation=True)
    outputs = model(**inputs)
    probas = torch.softmax(outputs.logits, dim=-1)
    probas_list = probas.tolist()[0]
    result_html = '<h3>Model Results</h3>'
    result_html += f'<p>Input text : {input_text}</p>'
    result_html += f'<p>Result : {probas_list}</p>'
    
    return render_template_string(result_html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)