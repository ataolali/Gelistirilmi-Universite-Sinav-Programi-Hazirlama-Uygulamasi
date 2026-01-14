"""
Otomatik Sınav Planlama Algoritması (GÜNCELLENMİŞ - Hoca Kısıtı Dahil)
"""
from modeller import db, Course, Classroom, ExamSchedule, CourseStudent, ClassroomProximity, InstructorAvailability
from datetime import datetime, date, time, timedelta
import random

# --- AYARLAR ---
SINAV_GUNLERI = [
    date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), 
    date(2026, 1, 8), date(2026, 1, 9), 
    date(2026, 1, 12), date(2026, 1, 13), date(2026, 1, 14),
    date(2026, 1, 15), date(2026, 1, 16)
]

SINAV_SAATLERI = [
    time(9, 0), time(11, 0), time(13, 0), time(15, 0), time(17, 0)
]

def get_student_ids_for_course(course_id):
    """Bir dersi alan öğrencilerin ID listesi"""
    students = db.session.query(CourseStudent.student_no).filter_by(course_id=course_id).all()
    return {s[0] for s in students}

def check_conflict(course_students, exam_date, start_time, schedule_memory):
    """Öğrenci çakışma kontrolü"""
    for item in schedule_memory:
        if item['date'] == exam_date and item['time'] == start_time:
            common = course_students.intersection(item['students'])
            if common:
                return True # Çakışma VAR
    return False

def generate_exam_schedule():
    """Ana Planlama Fonksiyonu"""
    results = {'success': False, 'scheduled': 0, 'error': None}
    
    try:
        courses = Course.query.filter_by(has_exam=True).order_by(Course.student_count.desc()).all()
        
        if not courses:
            return {'success': False, 'error': 'Planlanacak ders bulunamadı.'}

        schedule_memory = []
        busy_rooms = {} 
        all_classrooms = Classroom.query.filter_by(is_available=True).order_by(Classroom.capacity.desc()).all()
        
        scheduled_count = 0
        unscheduled_courses = []

        # Sınavları günlere biraz dağıtmak için gün listesini karıştırabiliriz
        # Ama hafta sonu/sıra bozulmasın diye şimdilik sabit kalsın.
        # Hoca kısıtı zaten dağıtacak.

        for course in courses:
            course_students = get_student_ids_for_course(course.id)
            is_placed = False
            
            # --- YENİ EKLENEN KISIM: HOCA KISITLARINI ÇEK ---
            blocked_days_indices = [] # 0=Pzt, 1=Sal...
            if course.instructor_id:
                restrictions = InstructorAvailability.query.filter_by(course_id=course.id).all()
                for r in restrictions:
                    blocked_days_indices.append(r.day_of_week)
            # -----------------------------------------------

            for day in SINAV_GUNLERI:
                if is_placed: break
                
                # --- YENİ EKLENEN KONTROL ---
                # Eğer bugün hocanın yasaklı günüyse, bu günü komple atla!
                if day.weekday() in blocked_days_indices:
                    print(f"  🚫 {course.code} için {day} atlandı (Hoca Müsait Değil)")
                    continue
                # -----------------------------

                for slot in SINAV_SAATLERI:
                    if is_placed: break
                    
                    # 1. Öğrenci Çakışması
                    if check_conflict(course_students, day, slot, schedule_memory):
                        continue 
                    
                    # 2. Sınıf Bulma
                    required_cap = course.student_count
                    occupied_rooms = busy_rooms.get((day, slot), [])
                    free_rooms = [r for r in all_classrooms if r.id not in occupied_rooms]
                    
                    if not free_rooms: continue

                    assigned_rooms = []
                    # A) Tek sınıf
                    for room in free_rooms:
                        if room.capacity >= required_cap:
                            assigned_rooms = [room]
                            break
                    
                    # B) Yakın sınıf
                    if not assigned_rooms:
                        for main_room in free_rooms:
                            current_cap = main_room.capacity
                            temp_assigned = [main_room]
                            
                            prox = ClassroomProximity.query.filter(
                                ((ClassroomProximity.classroom1_id == main_room.id) | 
                                 (ClassroomProximity.classroom2_id == main_room.id))
                            ).all()
                            nearby_ids = {p.classroom1_id if p.classroom2_id == main_room.id else p.classroom2_id for p in prox}
                            valid_neighbors = [r for r in free_rooms if r.id in nearby_ids and r.id != main_room.id]
                            
                            for neighbor in valid_neighbors:
                                temp_assigned.append(neighbor)
                                current_cap += neighbor.capacity
                                if current_cap >= required_cap:
                                    assigned_rooms = temp_assigned
                                    break
                            if assigned_rooms: break 
                    
                    if assigned_rooms:
                        # KAYDET
                        main_room = assigned_rooms[0]
                        extras = ",".join([r.name for r in assigned_rooms[1:]]) if len(assigned_rooms) > 1 else None
                        
                        exam = ExamSchedule(
                            course_id=course.id,
                            classroom_id=main_room.id,
                            teacher_id=course.instructor_id,
                            exam_date=day,
                            start_time=slot,
                            end_time=(datetime.combine(day, slot) + timedelta(minutes=course.exam_duration)).time(),
                            additional_classrooms=extras
                        )
                        db.session.add(exam)
                        
                        schedule_memory.append({
                            'date': day, 'time': slot, 'students': course_students
                        })
                        
                        if (day, slot) not in busy_rooms: busy_rooms[(day, slot)] = []
                        for r in assigned_rooms:
                            busy_rooms[(day, slot)].append(r.id)
                            
                        is_placed = True
                        scheduled_count += 1
            
            if not is_placed:
                unscheduled_courses.append(course.code)

        db.session.commit()
        
        results['success'] = True
        results['scheduled'] = scheduled_count
        if unscheduled_courses:
            results['error'] = f"Uyarı: {len(unscheduled_courses)} ders yerleşemedi."
            
        return results

    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}