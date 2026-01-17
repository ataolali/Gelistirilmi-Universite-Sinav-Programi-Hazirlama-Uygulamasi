"""
Flask ana uygulama dosyası - Otomatik Ders ve Bölüm Oluşturma Eklendi
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from modeller import db, User, Faculty, Department, Course, CourseStudent, Classroom, ClassroomProximity, ExamSchedule, InstructorAvailability
from datetime import datetime, time, date, timedelta
import os
import json
import unidecode

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

def ensure_defaults():
    fac = Faculty.query.first()
    if not fac:
        fac = Faculty(name="Mühendislik ve Doğa Bilimleri", code="MDBF")
        db.session.add(fac)
        db.session.commit()
    
    dept = Department.query.first()
    if not dept:
        dept = Department(name="Genel Mühendislik", code="GENEL", faculty_id=fac.id)
        db.session.add(dept)
        db.session.commit()
    
    return dept.id

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
    if current_user.is_admin(): return render_template('admin_dashboard.html')
    elif current_user.is_department_head(): return render_template('department_dashboard.html')
    elif current_user.is_teacher(): return render_template('teacher_dashboard.html')
    else: return render_template('student_dashboard.html')

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
            exam_type=request.form.get('exam_type', 'yazılı'), has_exam=request.form.get('has_exam') == 'on'
        ))
        db.session.commit()
        flash('Ders eklendi!', 'success')
        return redirect(url_for('list_courses'))
    return render_template('add_course.html', departments=Department.query.all(), teachers=User.query.filter_by(role='teacher').all())

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

# --- GÜNCELLENMİŞ VE GÜVENLİ PROGRAM GÖRÜNTÜLEME ---
# --- GÜNCELLENMİŞ PROGRAM GÖRÜNTÜLEME (HTML İLE UYUMLU) ---
@app.route('/program')
@login_required
def programi_goruntule():
    if current_user.is_admin(): 
        raw_schedules = ExamSchedule.query.all()
    elif current_user.is_teacher(): 
        raw_schedules = ExamSchedule.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.is_student():
        try:
            courses = Course.query.join(CourseStudent).filter(CourseStudent.student_no == current_user.username).all()
            raw_schedules = ExamSchedule.query.filter(ExamSchedule.course_id.in_([c.id for c in courses])).all()
        except:
            raw_schedules = []
    else: 
        raw_schedules = []

    # GRUPLAMA MANTIĞI: Aynı Tarih, Saat ve Sınıftakileri Birleştir
    grouped_schedules = {}
    
    for sch in raw_schedules:
        # Veri bütünlüğü kontrolü
        if not sch.course or not sch.classroom: continue

        key = (sch.exam_date, sch.start_time, sch.classroom_id)
        
        if key not in grouped_schedules:
            grouped_schedules[key] = {
                'date': sch.exam_date,
                'time': sch.start_time,
                'classroom': sch.classroom,
                'additional_classrooms': sch.additional_classrooms,
                'teacher': sch.teacher,
                'courses': [sch.course],
                'course_codes_str': sch.course.code,
                'course_name': sch.course.name 
            }
        else:
            if sch.course not in grouped_schedules[key]['courses']:
                grouped_schedules[key]['courses'].append(sch.course)
            
            # Kodları yan yana ekle (BLM101, SEC130 gibi)
            if sch.course.code not in grouped_schedules[key]['course_codes_str']:
                grouped_schedules[key]['course_codes_str'] += f", {sch.course.code}"
    
    final_list = list(grouped_schedules.values())
    final_list.sort(key=lambda x: (x['date'], x['time']))

    # is_grouped=True parametresiyle gönderiyoruz
    return render_template('program.html', schedules=final_list, is_grouped=True)

@app.route('/cikti/<format_type>')
@login_required
def cikti_al(format_type):
    from cikti_araclari import pdf_cikti_al, excel_cikti_al
    schedules = ExamSchedule.query.all()
    if format_type == 'pdf': return send_file(pdf_cikti_al(schedules), as_attachment=True, download_name='sinav_programi.pdf')
    elif format_type == 'excel': return send_file(excel_cikti_al(schedules), as_attachment=True, download_name='sinav_programi.xlsx')
    return redirect(url_for('programi_goruntule'))

# --- BURASI YENİ YAPIDIR (PAKET FORMATINI ALIR) ---
@app.route('/admin/import-pdfs', methods=['POST'])
@login_required
def import_pdfs():
    if not current_user.is_admin(): return redirect(url_for('dashboard'))
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')

    if not os.path.exists(data_dir):
        flash(f"'{data_dir}' klasörü bulunamadı!", 'error')
        return redirect(url_for('dashboard'))

    try:
        default_dept_id = ensure_defaults()
        # ARTIK STUDENTS_DATA {CODE: {STUDENTS: [], NAME: ""}} FORMATINDA
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

        # 2. Dersleri Kaydet
        for course_code, data in students_data.items():
            students = data['students']
            course_name = data['name']
            
            if not students: continue
            
            course = Course.query.filter_by(code=course_code).first()
            if not course:
                course = Course(
                    code=course_code,
                    name=course_name, # MANUEL LİSTEDEN GELEN DOĞRU İSİM
                    department_id=default_dept_id,
                    exam_duration=60,
                    has_exam=True
                )
                db.session.add(course)
                db.session.commit()
            else:
                course.name = course_name # İsim güncelle
                db.session.commit()
            
            # Öğrencileri Ekle
            for student in students:
                exist = CourseStudent.query.filter_by(course_id=course.id, student_no=student['student_no']).first()
                if not exist:
                    db.session.add(CourseStudent(course_id=course.id, student_no=student['student_no'], student_name=student['name']))
                
                user_exist = User.query.filter_by(username=student['student_no']).first()
                if not user_exist:
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
        
        # Yakınlıklar
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
        
        # Hoca Hesapları
        teachers = ['Elif Pinar Hacibeyoglu', 'Cuneyt Yazici', 'Vildan Yazici', 'Orkun Karabatak']
        for t_name in teachers:
            u_name = unidecode.unidecode(t_name.lower().replace(' ', ''))
            if not User.query.filter_by(username=u_name).first():
                t_user = User(username=u_name, email=f'{u_name}@kostu.edu.tr', role='teacher', name=t_name)
                t_user.set_password('123456')
                db.session.add(t_user)
        db.session.commit()
        
        import random
        all_courses = Course.query.all()
        all_teachers = User.query.filter_by(role='teacher').all()
        if all_teachers:
            for c in all_courses:
                if not c.instructor_id:
                    t = random.choice(all_teachers)
                    c.instructor_id = t.id
            db.session.commit()

        flash(f'Tüm veriler başarıyla yüklendi!', 'success')
    
    except Exception as e:
        flash(f'Veri yükleme hatası: {str(e)}', 'error')
        print(f"HATA: {e}")

    return redirect(url_for('dashboard'))

@app.route('/teacher/availability', methods=['GET', 'POST'])
@login_required
def teacher_availability():
    if not current_user.is_teacher():
        flash('Bu sayfaya sadece hocalar girebilir!', 'error')
        return redirect(url_for('dashboard'))
    
    my_courses = Course.query.filter_by(instructor_id=current_user.id).all()
    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    blocked_days = []
    
    if my_courses:
        restrictions = InstructorAvailability.query.filter_by(course_id=my_courses[0].id).all()
        for r in restrictions:
            blocked_days.append(r.day_of_week)

    if request.method == 'POST':
        try:
            selected_days = request.form.getlist('unavailable_days')
            for course in my_courses:
                InstructorAvailability.query.filter_by(course_id=course.id).delete()
                for day_str in selected_days:
                    day_idx = int(day_str)
                    av = InstructorAvailability(course_id=course.id, day_of_week=day_idx, start_time=time(0,0), end_time=time(23,59))
                    db.session.add(av)
            db.session.commit()
            flash('Müsaitlik durumu güncellendi!', 'success')
            return redirect(url_for('teacher_availability'))
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
    
    return render_template('teacher_availability.html', courses=my_courses, blocked_days=blocked_days, day_names=day_names)

# --- ANA.PY DOSYASININ EN ALTI ---


if __name__ == '__main__':
    with app.app_context():
        # 1. Eski veritabanını tamamen uçur (Hatayı çözen kısım)
        print("⚠️ Eski veritabanı temizleniyor...")
        db.drop_all()
        
        # 2. Yenisini tertemiz oluştur
        print("✅ Yeni tablolar oluşturuluyor...")
        db.create_all()
        
        # 3. Admin hesabını tekrar aç
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@kostu.edu.tr', role='admin', name='Sistem Yöneticisi')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("👤 Admin hesabı oluşturuldu.")

    print("🚀 Server başlatılıyor...")
    app.run(debug=True, port=5000)