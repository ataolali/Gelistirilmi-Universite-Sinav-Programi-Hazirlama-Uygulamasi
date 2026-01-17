from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'teacher', 'student', 'department_head'
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self): return self.role == 'admin'
    def is_teacher(self): return self.role == 'teacher'
    def is_student(self): return self.role == 'student'
    def is_department_head(self): return self.role == 'department_head'

class Faculty(db.Model):
    __tablename__ = 'faculties'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True)
    departments = db.relationship('Department', backref='faculty', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=False)
    is_myo = db.Column(db.Boolean, default=False)
    courses = db.relationship('Course', backref='department', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    exam_duration = db.Column(db.Integer, default=60)
    exam_type = db.Column(db.String(20), default='yazılı')
    has_exam = db.Column(db.Boolean, default=True)
    special_classroom = db.Column(db.String(50))
    special_duration = db.Column(db.Integer)
    student_count = db.Column(db.Integer, default=0)
    
    # İlişki
    students = db.relationship('CourseStudent', backref='course', lazy=True)
    instructor = db.relationship('User', backref='courses')

class CourseStudent(db.Model):
    __tablename__ = 'course_students'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_no = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100))

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    exam_type_support = db.Column(db.String(20), default='yazılı')

class ClassroomProximity(db.Model):
    __tablename__ = 'classroom_proximities'
    id = db.Column(db.Integer, primary_key=True)
    classroom1_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    classroom2_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)

class ExamSchedule(db.Model):
    __tablename__ = 'exam_schedules'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    additional_classrooms = db.Column(db.String(200)) # Ek derslikler (Metin olarak)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # İlişkiler
    course = db.relationship('Course', backref='exams')
    classroom = db.relationship('Classroom', backref='exams')
    teacher = db.relationship('User', backref='proctored_exams')

    # ÖNEMLİ: UniqueConstraint KALDIRILDI!
    # Artık aynı sınıfa aynı saatte birden fazla ders atanabilir (Ortak Sınav İçin)

class InstructorAvailability(db.Model):
    __tablename__ = 'instructor_availability'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Pazartesi, 6=Pazar
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)