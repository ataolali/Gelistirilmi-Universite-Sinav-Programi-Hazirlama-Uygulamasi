"""
Flask ana uygulama dosyası - Otomatik Ders ve Bölüm Oluşturma Eklendi
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from modeller import db, User, Faculty, Department, Course, CourseStudent, Classroom, ClassroomProximity, ExamSchedule, InstructorAvailability
from datetime import datetime, time, date, timedelta
import os
import json

# Excel modülünü çağırıyoruz
from excel_ayiklayici import import_all_data

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli-anahtar-uretimde-degistirin'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sinav_programi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value)
    except:
        return []

# --- Yardımcı Fonksiyon: Varsayılanları Oluştur ---
def ensure_defaults():
    """Derslerin eklenebilmesi için varsayılan Fakülte ve Bölüm oluşturur."""
    # 1. Fakülte Var mı?
    fac = Faculty.query.first()
    if not fac:
        fac = Faculty(name="Mühendislik ve Doğa Bilimleri", code="MDBF")
        db.session.add(fac)
        db.session.commit()
        print("✅ Varsayılan Fakülte oluşturuldu.")
    
    # 2. Bölüm Var mı?
    dept = Department.query.first()
    if not dept:
        dept = Department(name="Genel Mühendislik", code="GENEL", faculty_id=fac.id)
        db.session.add(dept)
        db.session.commit()
        print("✅ Varsayılan Bölüm oluşturuldu.")
    
    return dept.id

# Ana sayfa
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Kullanıcı adı veya şifre hatalı!', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return render_template('admin_dashboard.html')
    elif current_user.is_department_head():
        return render_template('department_dashboard.html')
    elif current_user.is_teacher():
        return render_template('teacher_dashboard.html')
    else:
        return render_template('student_dashboard.html')

# Admin: Fakülte/Bölüm yönetimi
@app.route('/admin/faculties', methods=['GET', 'POST'])
@login_required
def manage_faculties():
    if not current_user.is_admin(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        db.session.add(Faculty(name=request.form.get('name'), code=request.form.get('code')))
        db.session.commit()
        flash('Fakülte eklendi!', 'success')
        return redirect(url_for('manage_faculties'))
    return render_template('manage_faculties.html', faculties=Faculty.query.all())

@app.route('/admin/departments', methods=['GET', 'POST'])
@login_required
def manage_departments():
    if not current_user.is_admin(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        db.session.add(Department(name=request.form.get('name'), code=request.form.get('code'), faculty_id=request.form.get('faculty_id'), is_myo=request.form.get('is_myo') == 'on'))
        db.session.commit()
        flash('Bölüm eklendi!', 'success')
        return redirect(url_for('manage_departments'))
    return render_template('manage_departments.html', departments=Department.query.all(), faculties=Faculty.query.all())

# Ders yönetimi
@app.route('/courses', methods=['GET'])
@login_required
def list_courses():
    if current_user.is_admin(): courses = Course.query.all()
    elif current_user.is_department_head(): courses = Course.query.join(Department).filter(Department.id == current_user.department).all()
    elif current_user.is_teacher(): courses = Course.query.filter_by(instructor_id=current_user.id).all()
    else: courses = []
    return render_template('courses.html', courses=courses)

@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if not (current_user.is_admin() or current_user.is_department_head()): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        db.session.add(Course(
            code=request.form.get('code'), name=request.form.get('name'), department_id=request.form.get('department_id'),
            instructor_id=request.form.get('instructor_id') or None, exam_duration=int(request.form.get('exam_duration', 90)),
            exam_type=request.form.get('exam_type', 'yazılı'), has_exam=request.form.get('has_exam') == 'on',
            special_classroom=request.form.get('special_classroom') or None, special_duration=int(request.form.get('special_duration')) if request.form.get('special_duration') else None
        ))
        db.session.commit()
        flash('Ders eklendi!', 'success')
        return redirect(url_for('list_courses'))
    return render_template('add_course.html', departments=Department.query.all(), teachers=User.query.filter_by(role='teacher').all())

# Derslik yönetimi
@app.route('/classrooms', methods=['GET', 'POST'])
@login_required
def manage_classrooms():
    if not (current_user.is_admin() or current_user.is_department_head()): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        db.session.add(Classroom(name=request.form.get('name'), capacity=int(request.form.get('capacity')), is_available=request.form.get('is_available') == 'on'))
        db.session.commit()
        flash('Derslik eklendi!', 'success')
        return redirect(url_for('manage_classrooms'))
    return render_template('classrooms.html', classrooms=Classroom.query.all())

# Otomatik planlama
@app.route('/planning/auto', methods=['POST'])
@login_required
def auto_planning():
    if not (current_user.is_admin() or current_user.is_department_head()): return jsonify({'error': 'Yetkiniz yok!'}), 403
    from planlama_algoritmasi import generate_exam_schedule
    ExamSchedule.query.delete()
    db.session.commit()
    result = generate_exam_schedule()
    if result.get('success'):
        flash(f"Planlama tamamlandı! {result.get('scheduled', 0)} ders planlandı.", 'success')
        return jsonify({'success': True, 'scheduled': result.get('scheduled', 0)})
    else:
        flash(f"Planlama hatası: {result.get('error')}", 'error')
        return jsonify({'success': False, 'error': result.get('error')})

@app.route('/program')
@login_required
def programi_goruntule():
    if current_user.is_admin(): schedules = ExamSchedule.query.all()
    elif current_user.is_teacher(): schedules = ExamSchedule.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.is_student():
        courses = Course.query.join(CourseStudent).filter(CourseStudent.student_no == current_user.username).all()
        schedules = ExamSchedule.query.filter(ExamSchedule.course_id.in_([c.id for c in courses])).all()
    else: schedules = []
    return render_template('program.html', schedules=schedules)

@app.route('/cikti/<format_type>')
@login_required
def cikti_al(format_type):
    from cikti_araclari import pdf_cikti_al, excel_cikti_al
    schedules = ExamSchedule.query.all()
    if format_type == 'pdf': return send_file(pdf_cikti_al(schedules), as_attachment=True, download_name='sinav_programi.pdf')
    elif format_type == 'excel': return send_file(excel_cikti_al(schedules), as_attachment=True, download_name='sinav_programi.xlsx')
    return redirect(url_for('programi_goruntule'))

# --- GÜNCELLENMİŞ IMPORT FONKSİYONU (ana.py içine) ---
#
import unidecode 

@app.route('/admin/import-pdfs', methods=['POST'])
@login_required
def import_pdfs():
    if not current_user.is_admin(): return redirect(url_for('dashboard'))
    data_dir = 'data'
    if not os.path.exists(data_dir):
        flash(f"'{data_dir}' klasörü bulunamadı!", 'error')
        return redirect(url_for('dashboard'))

    try:
        default_dept_id = ensure_defaults()
        # Verileri oku
        students_data, proximity_data, tum_derslikler, room_capacities = import_all_data(data_dir)
        
        # 1. Derslikleri Kaydet
        for derslik_adi in tum_derslikler:
            if derslik_adi and len(derslik_adi) <= 20:
                kapasite = room_capacities.get(derslik_adi, 40)
                existing = Classroom.query.filter_by(name=derslik_adi).first()
                if not existing:
                    db.session.add(Classroom(name=derslik_adi, capacity=kapasite, is_available=True))
                else:
                    existing.capacity = kapasite

        added_courses = 0
        
        # 2. Dersleri ve Öğrencileri Kaydet
        for course_code, students in students_data.items():
            if not students: continue
            
            # Ders Oluşturma
            course = Course.query.filter_by(code=course_code).first()
            if not course:
                course = Course(
                    code=course_code,
                    name=f"{course_code} Dersi",
                    department_id=default_dept_id,
                    exam_duration=60,
                    has_exam=True
                )
                db.session.add(course)
                db.session.commit()
                added_courses += 1
            
            # Öğrencileri Döngüye Al
            for student in students:
                # A) Öğrenciyi Derse Ekle (CourseStudent Tablosu)
                exist = CourseStudent.query.filter_by(course_id=course.id, student_no=student['student_no']).first()
                if not exist:
                    db.session.add(CourseStudent(course_id=course.id, student_no=student['student_no'], student_name=student['name']))
                
                # B) Öğrenciye HESAP Aç (User Tablosu) - ARTIK BAĞIMSIZ ÇALIŞIYOR
                # Şifre: 123456
                user_exist = User.query.filter_by(username=student['student_no']).first()
                if not user_exist:
                    # İsim boş gelirse "Ogrenci" yaz
                    std_name = student['name'] if student['name'] else "Ogrenci"
                    new_student_user = User(
                        username=student['student_no'],
                        email=f"{student['student_no']}@ogrenci.kostu.edu.tr",
                        role='student',
                        name=std_name
                    )
                    new_student_user.set_password('123456')
                    db.session.add(new_student_user)

            course.student_count = len(students)
        
        # 3. Yakınlıkları Kaydet
        for prox in proximity_data:
            c1 = Classroom.query.filter_by(name=prox['classroom1']).first()
            c2 = Classroom.query.filter_by(name=prox['classroom2']).first()
            if c1 and c2:
                exist = ClassroomProximity.query.filter(
                    ((ClassroomProximity.classroom1_id == c1.id) & (ClassroomProximity.classroom2_id == c2.id)) |
                    ((ClassroomProximity.classroom1_id == c2.id) & (ClassroomProximity.classroom2_id == c1.id))
                ).first()
                if not exist:
                    db.session.add(ClassroomProximity(classroom1_id=c1.id, classroom2_id=c2.id))
        
        db.session.commit()
        
        # 4. Hoca Hesaplarını Güncelle (Eksik varsa ekle)
        teachers = ['Elif Pinar Hacibeyoglu', 'Cuneyt Yazici', 'Vildan Yazici', 'Orkun Karabatak']
        for t_name in teachers:
            u_name = unidecode.unidecode(t_name.lower().replace(' ', ''))
            if not User.query.filter_by(username=u_name).first():
                t_user = User(username=u_name, email=f'{u_name}@kostu.edu.tr', role='teacher', name=t_name)
                t_user.set_password('123456')
                db.session.add(t_user)
        db.session.commit()
        
        # Derslere Hoca Atama (Eğer boşsa)
        import random
        all_courses = Course.query.all()
        all_teachers = User.query.filter_by(role='teacher').all()
        if all_teachers:
            for c in all_courses:
                if not c.instructor_id:
                    t = random.choice(all_teachers)
                    c.instructor_id = t.id
            db.session.commit()

        msg = f'İşlem Tamam! Tüm eksik öğrenci ve hoca hesapları oluşturuldu.'
        flash(msg, 'success')
    
    except Exception as e:
        flash(f'Veri yükleme hatası: {str(e)}', 'error')
        print(f"HATA: {e}")

    return redirect(url_for('dashboard'))



# --- ÇOKLU GÜN DESTEKLİ FONKSİYON (ana.py) ---
@app.route('/teacher/availability', methods=['GET', 'POST'])
@login_required
def teacher_availability():
    if not current_user.is_teacher():
        flash('Bu sayfaya sadece hocalar girebilir!', 'error')
        return redirect(url_for('dashboard'))
    
    # Hocanın derslerini bul
    my_courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    # Gün İsimleri
    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    
    # Mevcut kısıtlamaları bul (Liste olarak)
    blocked_days = [] # Örn: [1, 3] -> Salı ve Perşembe
    
    if my_courses:
        # İlk dersin kısıtlarına bakmamız yeterli
        restrictions = InstructorAvailability.query.filter_by(course_id=my_courses[0].id).all()
        for r in restrictions:
            blocked_days.append(r.day_of_week)

    if request.method == 'POST':
        try:
            # Formdan seçilen günleri liste olarak al (checkbox)
            selected_days = request.form.getlist('unavailable_days') # ['0', '2'] gibi gelir
            
            # Önce tüm dersler için eski kısıtları temizle
            for course in my_courses:
                InstructorAvailability.query.filter_by(course_id=course.id).delete()
                
                # Yeni seçilen günleri ekle
                for day_str in selected_days:
                    day_idx = int(day_str)
                    av = InstructorAvailability(
                        course_id=course.id,
                        day_of_week=day_idx,
                        start_time=time(0,0),
                        end_time=time(23,59)
                    )
                    db.session.add(av)
            
            db.session.commit()
            
            if not selected_days:
                flash('Tüm kısıtlamalar kaldırıldı. Artık her gün müsaitsiniz.', 'success')
            else:
                flash('Müsaitlik durumu güncellendi!', 'success')
            
            return redirect(url_for('teacher_availability'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'error')
    
    return render_template('teacher_availability.html', 
                         courses=my_courses, 
                         blocked_days=blocked_days,
                         day_names=day_names)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@kostu.edu.tr', role='admin', name='Sistem Yöneticisi')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True, port=5000)


