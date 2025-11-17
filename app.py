from flask import Flask, jsonify, request, send_from_directory, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from wtforms import SelectField
import os


app = Flask(__name__, static_folder='static')
CORS(
    app,
    supports_credentials=True,
    resources={
        r"/api/*": {
            "origins": ["http://127.0.0.1:5000", "http://localhost:5000"]
        }
    },
)

# Secret key for session management
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Cookie configuration for session management
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usertype = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return self.username

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'usertype': self.usertype
        }

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_name = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    enrollments = db.relationship('Enrollment', backref='course', cascade='all, delete-orphan')

    def __repr__(self):
        return f"{self.course_name} ({self.course_code})"

    def to_dict(self):
        enrolled_count = len(self.enrollments)
        return {
            'id': self.id,
            'course_name': self.course_name,
            'course_code': self.course_code,
            'teacher_name': self.teacher_name,
            'time': self.time,
            'capacity': self.capacity,
            'enrolled_count': enrolled_count,
            'is_full': enrolled_count >= self.capacity
        }

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.Integer, nullable=True)

    student = db.relationship('User', backref='enrollments')

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.username if self.student else None,
            'course_id': self.course_id,
            'grade': self.grade
        }

class SecureModelView(ModelView):
    def is_accessible(self):
        return 'user_id' in session and session.get('usertype') == 2

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))
class EnrollmentModelView(SecureModelView):
    column_list = ['id', 'student', 'course', 'grade']
    column_labels = {
        'student': 'Student',
        'course': 'Course',
        'grade': 'Grade'
    }
    column_formatters = {
        'student': lambda v, c, m, p: m.student.username if m.student else 'N/A',
        'course': lambda v, c, m, p: f"{m.course.course_name} ({m.course.course_code})" if m.course else 'N/A'
    }
    column_sortable_list = ['id', 'grade']
    column_searchable_list = ['grade']
    form_columns = ['student', 'course', 'grade']

    def scaffold_form(self):
        form_class = super(EnrollmentModelView, self).scaffold_form()
        # Filter to show only students (usertype=0)
        form_class.student.query_factory = lambda: User.query.filter_by(usertype=0).all()
        return form_class
class CourseModelView(SecureModelView):
    column_list = ['id', 'course_name', 'course_code', 'teacher_name', 'time', 'capacity']
    form_columns = ['course_name', 'course_code', 'teacher_name', 'time', 'capacity']

    def scaffold_form(self):
        form_class = super(CourseModelView, self).scaffold_form()
        # Replace teacher_name field with a dropdown of teacher usernames
        form_class.teacher_name = SelectField(
            'Teacher',
            choices=lambda: [(t.username, t.username) for t in User.query.filter_by(usertype=1).all()]
        )
        return form_class



# Initialize Flask-Admin
admin = Admin(app, name='University Admin', template_mode='bootstrap3')

# Add model views to admin
admin.add_view(SecureModelView(User, db.session, name='Users'))
admin.add_view(CourseModelView(Course, db.session, name='Courses'))
admin.add_view(EnrollmentModelView(Enrollment, db.session, name='Enrollments'))


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Find user by username
    user = User.query.filter_by(username=username).first()

    if not user or user.password != password:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # Store user info in session
    session['user_id'] = user.id
    session['username'] = user.username
    session['usertype'] = user.usertype

    # Determine redirect URL based on usertype
    if user.usertype == 0:  # Student
        redirect_url = '/coursepage.html'
    elif user.usertype == 1:  # Teacher
        redirect_url = '/teacher.login.html'
    else:  # Admin (usertype == 2)
        redirect_url = '/admin.html'

    return jsonify({
        'success': True,
        'message': 'Login successful',
        'redirect': redirect_url,
        'user': user.to_dict()
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/api/current-user', methods=['GET'])
def current_user():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    return jsonify({'success': True, 'user': user.to_dict()})


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Get all courses
@app.route('/api/courses', methods=['GET'])
def get_courses():
    courses = Course.query.all()
    return jsonify({'success': True, 'courses': [course.to_dict() for course in courses]})


# Get student's enrolled courses
@app.route('/api/student/courses', methods=['GET'])
def get_student_courses():
    if 'user_id' not in session or session.get('usertype') != 0:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    enrollments = Enrollment.query.filter_by(student_id=session['user_id']).all()
    courses = [{'course': enrollment.course.to_dict(), 'grade': enrollment.grade}
               for enrollment in enrollments]

    return jsonify({'success': True, 'courses': courses})


# Enroll in a course
@app.route('/api/enroll', methods=['POST'])
def enroll_course():
    if 'user_id' not in session or session.get('usertype') != 0:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    course_id = data.get('course_id')

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'message': 'Course not found'}), 404

    if len(course.enrollments) >= course.capacity:
        return jsonify({'success': False, 'message': 'Course is full'}), 400

    existing = Enrollment.query.filter_by(student_id=session['user_id'], course_id=course_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already enrolled'}), 400

    enrollment = Enrollment(student_id=session['user_id'], course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Enrolled successfully'})


# Drop a course
@app.route('/api/drop', methods=['POST'])
def drop_course():
    if 'user_id' not in session or session.get('usertype') != 0:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    course_id = data.get('course_id')

    enrollment = Enrollment.query.filter_by(student_id=session['user_id'], course_id=course_id).first()
    if not enrollment:
        return jsonify({'success': False, 'message': 'Not enrolled in this course'}), 404

    db.session.delete(enrollment)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Dropped successfully'})


# Get teacher's courses with students
@app.route('/api/teacher/courses', methods=['GET'])
def get_teacher_courses():
    if 'user_id' not in session or session.get('usertype') != 1:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    teacher_username = session.get('username')
    courses = Course.query.filter_by(teacher_name=teacher_username).all()
    result = []

    for course in courses:
        course_data = course.to_dict()
        course_data['students'] = [enrollment.to_dict() for enrollment in course.enrollments]
        result.append(course_data)

    return jsonify({'success': True, 'courses': result})



# Update student grade
@app.route('/api/grade', methods=['PUT'])
def update_grade():
    if 'user_id' not in session or session.get('usertype') != 1:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    enrollment_id = data.get('enrollment_id')
    grade = data.get('grade')

    enrollment = Enrollment.query.get(enrollment_id)
    if not enrollment:
        return jsonify({'success': False, 'message': 'Enrollment not found'}), 404

    # Check if the logged-in teacher's username matches the course's teacher_name
    if enrollment.course.teacher_name != session['username']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    enrollment.grade = grade
    db.session.commit()

    return jsonify({'success': True, 'message': 'Grade updated successfully'})



if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if User.query.count() == 0:
            users = [
                User(usertype=0, username='student1', password='pass123'),
                User(usertype=0, username='student2', password='pass123'),
                User(usertype=1, username='teacher1', password='pass123'),
                User(usertype=1, username='teacher2', password='pass123'),
                User(usertype=2, username='admin1', password='pass123'),
            ]
            db.session.add_all(users)
            db.session.commit()

            # Add sample courses using teacher names
            courses = [
                Course(course_name='Math 032', course_code='MATH032', teacher_name='teacher1', time='MWF 9:00-10:00', capacity=30),
                Course(course_name='Math 024', course_code='MATH024', teacher_name='teacher1', time='TTh 11:00-12:30', capacity=25),
                Course(course_name='CS 162', course_code='CS162', teacher_name='teacher2', time='MWF 2:00-3:00', capacity=20),
                Course(course_name='CS 106', course_code='CS106', teacher_name='teacher2', time='TTh 3:30-5:00', capacity=35),
            ]
            db.session.add_all(courses)
            db.session.commit()

            print("Sample data created successfully")

    app.run(debug=True)
