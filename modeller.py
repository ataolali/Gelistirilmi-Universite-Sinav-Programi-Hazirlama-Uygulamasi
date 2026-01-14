"""
Veritabanı modelleri
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Kullanıcı modeli"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    courses = db.relationship('Course', backref='instructor', lazy=True, foreign_keys='Course.instructor_id')
    exam_schedules = db.relationship('ExamSchedule', backref='teacher', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_department_head(self):
        return self.role == 'department'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'


class Faculty(db.Model):
    """Fakülte modeli"""
    __tablename__ = 'faculties'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=True)
    
    # İlişkiler
    departments = db.relationship('Department', backref='faculty', lazy=True, cascade='all, delete-orphan')


class Department(db.Model):
    """Bölüm/Program modeli"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'), nullable=False)
    is_myo = db.Column(db.Boolean, default=False)
    
    # İlişkiler
    courses = db.relationship('Course', backref='department', lazy=True, cascade='all, delete-orphan')


class Course(db.Model):
    """Ders modeli"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_count = db.Column(db.Integer, default=0)
    exam_duration = db.Column(db.Integer, default=90)
    exam_type = db.Column(db.String(50), default='yazılı')
    has_exam = db.Column(db.Boolean, default=True)
    special_classroom = db.Column(db.String(100), nullable=True)
    special_duration = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    students = db.relationship('CourseStudent', backref='course', lazy=True, cascade='all, delete-orphan')
    instructor_availability = db.relationship('InstructorAvailability', backref='course', lazy=True, cascade='all, delete-orphan')
    exam_schedules = db.relationship('ExamSchedule', backref='course', lazy=True, cascade='all, delete-orphan')


class CourseStudent(db.Model):
    """Derse kayıtlı öğrenci"""
    __tablename__ = 'course_students'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_no = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('course_id', 'student_no', name='unique_course_student'),)


class InstructorAvailability(db.Model):
    """Öğretim üyesi müsaitlik durumu"""
    __tablename__ = 'instructor_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)


class Classroom(db.Model):
    """Derslik modeli"""
    __tablename__ = 'classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    exam_schedules = db.relationship('ExamSchedule', backref='classroom', lazy=True)
    proximity_from = db.relationship('ClassroomProximity', foreign_keys='ClassroomProximity.classroom1_id', backref='classroom1', lazy=True)
    proximity_to = db.relationship('ClassroomProximity', foreign_keys='ClassroomProximity.classroom2_id', backref='classroom2', lazy=True)


class ClassroomProximity(db.Model):
    """Derslik yakınlık ilişkisi"""
    __tablename__ = 'classroom_proximity'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom1_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    classroom2_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('classroom1_id', 'classroom2_id', name='unique_proximity'),)


class ExamSchedule(db.Model):
    """Sınav programı"""
    __tablename__ = 'exam_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    additional_classrooms = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'exam_date', 'start_time', name='unique_classroom_time'),
    )
