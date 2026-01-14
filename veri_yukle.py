"""
PDF'lerden veri çıkarıp veritabanına yükleyen script
"""
from ana import app
from modeller import db, Course, CourseStudent, Classroom, ClassroomProximity
from pdf_ayiklayici import parse_all_pdfs
from pathlib import Path

def yukle():
    with app.app_context():
        pdf_dir = 'Yeni klasör'
        students_data, proximity_data, tum_derslikler = parse_all_pdfs(pdf_dir)
        
        print("\n=== Öğrenci Verileri Yükleniyor ===")
        for course_code, students in students_data.items():
            course = Course.query.filter_by(code=course_code).first()
            if course:
                print(f"{course_code}: {len(students)} öğrenci bulundu")
                for student in students:
                    existing = CourseStudent.query.filter_by(
                        course_id=course.id,
                        student_no=student['student_no']
                    ).first()
                    if not existing:
                        cs = CourseStudent(
                            course_id=course.id,
                            student_no=student['student_no'],
                            student_name=student['name']
                        )
                        db.session.add(cs)
                course.student_count = len(students)
            else:
                print(f"UYARI: {course_code} dersi bulunamadı!")
        
        print("\n=== Derslik Yakınlık Verileri Yükleniyor ===")
        print(f"Toplam {len(tum_derslikler)} farklı derslik bulundu")
        
        for derslik_adi in tum_derslikler:
            if not derslik_adi or len(derslik_adi) > 50:
                continue
            existing = Classroom.query.filter_by(name=derslik_adi).first()
            if not existing:
                classroom = Classroom(
                    name=derslik_adi,
                    capacity=50,
                    is_available=True
                )
                db.session.add(classroom)
                print(f"Yeni derslik eklendi: {derslik_adi}")
        
        db.session.commit()
        
        print("\n=== Yakınlık İlişkileri Yükleniyor ===")
        for prox in proximity_data:
            c1 = Classroom.query.filter_by(name=prox['classroom1']).first()
            c2 = Classroom.query.filter_by(name=prox['classroom2']).first()
            if c1 and c2:
                existing = ClassroomProximity.query.filter(
                    ((ClassroomProximity.classroom1_id == c1.id) & (ClassroomProximity.classroom2_id == c2.id)) |
                    ((ClassroomProximity.classroom1_id == c2.id) & (ClassroomProximity.classroom2_id == c1.id))
                ).first()
                if not existing:
                    cp = ClassroomProximity(classroom1_id=c1.id, classroom2_id=c2.id)
                    db.session.add(cp)
        
        db.session.commit()
        print(f"\nToplam {len(proximity_data)} yakınlık ilişkisi eklendi")
        print("\nVeri yükleme tamamlandı!")

if __name__ == '__main__':
    yukle()
