
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow frontend to call backend

@app.route('/')
def home():
    return "Hello from Flask Backend!"

if __name__ == '__main__':
    app.run(debug=True)

