# Sample Flask application
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'demo-api'})

@app.route('/api/users')
def get_users():
    # Sample users data
    users = [
        {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
        {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
    ]
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True)
