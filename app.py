from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# Database configuration dd
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    usertype = db.Column(db.Integer, primary_key=True) # 0 for student, 1 for teacher, 2 for admin
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {'username': self.username, 'email': self.email}


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        users = [
            User(usertype=0, username='student1', password='pass123'),
            User(usertype=1, username='teacher1', password='pass123'),
            User(usertype=2, username='admin1', password='pass123'),
        ]

        db.session.add_all(users)
        db.session.commit()
    app.run(debug=True)
