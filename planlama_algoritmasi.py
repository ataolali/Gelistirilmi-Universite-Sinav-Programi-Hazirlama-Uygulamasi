from modeller import db, Course, Classroom, ExamSchedule, CourseStudent, ClassroomProximity, InstructorAvailability
from datetime import datetime, date, time, timedelta
import random

# Sınav Takvimi
SINAV_GUNLERI = [
    date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), 
    date(2026, 1, 8), date(2026, 1, 9), 
    date(2026, 1, 12), date(2026, 1, 13), date(2026, 1, 14),
    date(2026, 1, 15), date(2026, 1, 16)
]
SINAV_SAATLERI = [time(9, 0), time(11, 0), time(13, 0), time(15, 0), time(17, 0)]

def get_student_ids_for_course_list(course_list):
    """Bir ders GRUBUNDAKİ tüm öğrencilerin ID kümesini döner"""
    all_students = set()
    for course in course_list:
        students = db.session.query(CourseStudent.student_no).filter_by(course_id=course.id).all()
        for s in students:
            all_students.add(s[0])
    return all_students

def check_conflict(student_set, exam_date, start_time, schedule_memory):
    """Çakışma Kontrolü"""
    for item in schedule_memory:
        if item['date'] == exam_date and item['time'] == start_time:
            # Kesişim var mı? (Ortak öğrenci var mı?)
            if student_set.intersection(item['students']):
                return True
    return False

def generate_exam_schedule():
    """Ana Planlama Fonksiyonu - GRUPLU VE ORTAK SINAV DESTEKLİ"""
    results = {'success': False, 'scheduled': 0, 'error': None}
    
    try:
        all_courses = Course.query.filter_by(has_exam=True).all()
        if not all_courses:
            return {'success': False, 'error': 'Planlanacak ders bulunamadı.'}

        # 1. DERSLERİ İSİMLERİNE GÖRE GRUPLA
        course_groups = {}
        for c in all_courses:
            # Boşlukları temizle ve büyük harf yap ki eşleşsin
            clean_name = c.name.strip().upper()
            if clean_name not in course_groups:
                course_groups[clean_name] = []
            course_groups[clean_name].append(c)
        
        # Grupları öğrenci sayısına göre sırala (En kalabalık grup en başa)
        sorted_groups = []
        for name, c_list in course_groups.items():
            total_students = sum(c.student_count for c in c_list)
            sorted_groups.append({'courses': c_list, 'total_count': total_students, 'name': name})
        
        sorted_groups.sort(key=lambda x: x['total_count'], reverse=True)

        schedule_memory = []
        busy_rooms = {} 
        all_classrooms = Classroom.query.filter_by(is_available=True).order_by(Classroom.capacity.desc()).all()
        
        scheduled_count = 0
        unscheduled_groups = []

        print("🚀 Ortak Sınav Planlaması Başlıyor...")

        for group in sorted_groups:
            course_list = group['courses']
            group_name = group['name']
            required_cap = group['total_count']
            
            # Gruptaki TÜM öğrencileri topla (Çakışma kontrolü için)
            group_students = get_student_ids_for_course_list(course_list)
            
            # Hoca Kısıtlarını Topla
            blocked_days_indices = set()
            for c in course_list:
                if c.instructor_id:
                    restrictions = InstructorAvailability.query.filter_by(course_id=c.id).all()
                    for r in restrictions:
                        blocked_days_indices.add(r.day_of_week)
            
            is_placed = False

            for day in SINAV_GUNLERI:
                if is_placed: break
                if day.weekday() in blocked_days_indices: continue # Hoca müsait değilse geç

                for slot in SINAV_SAATLERI:
                    if is_placed: break
                    
                    # 1. Çakışma Kontrolü
                    if check_conflict(group_students, day, slot, schedule_memory):
                        continue 
                    
                    # 2. Sınıf Bulma
                    occupied_rooms = busy_rooms.get((day, slot), [])
                    free_rooms = [r for r in all_classrooms if r.id not in occupied_rooms]
                    
                    if not free_rooms: continue

                    assigned_rooms = []
                    
                    # A) Tek sınıf yetiyor mu?
                    for room in free_rooms:
                        if room.capacity >= required_cap:
                            assigned_rooms = [room]
                            break
                    
                    # B) Yetmiyorsa: Yakınlık algoritması (Ek Sınıf)
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
                    
                    # Yerleşti mi?
                    if assigned_rooms:
                        main_room = assigned_rooms[0]
                        extras = ",".join([r.name for r in assigned_rooms[1:]]) if len(assigned_rooms) > 1 else None
                        
                        # GRUPTAKİ HER DERSİ AYNI YERE KAYDET
                        for course in course_list:
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
                            scheduled_count += 1
                        
                        schedule_memory.append({'date': day, 'time': slot, 'students': group_students})
                        
                        if (day, slot) not in busy_rooms: busy_rooms[(day, slot)] = []
                        for r in assigned_rooms:
                            busy_rooms[(day, slot)].append(r.id)
                            
                        is_placed = True

            if not is_placed:
                unscheduled_groups.append(group_name)

        db.session.commit()
        
        results['success'] = True
        results['scheduled'] = scheduled_count
        if unscheduled_groups:
            results['error'] = f"Yerleşemeyen: {len(unscheduled_groups)} grup."
            
        return results

    except Exception as e:
        print(f"HATA: {e}")
        db.session.rollback()
        return {'success': False, 'error': str(e)}