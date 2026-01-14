import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

def pdf_cikti_al(schedules):
    """
    Sınav programını PDF olarak oluşturur.
    Sütun taşmalarını engellemek için metin kaydırma (text wrapping) özelliği eklenmiştir.
    """
    filename = "sinav_programi.pdf"
    
    # PDF Ayarları
    # Kenar boşluklarını (margins) ayarlayarak tabloya daha fazla yer açtık.
    doc = SimpleDocTemplate(
        filename, 
        pagesize=A4,
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=18
    )
    
    elements = []
    
    # Stilleri Al
    styles = getSampleStyleSheet()
    
    # Başlık Stili
    title_style = styles['Title']
    title_style.fontName = 'Helvetica-Bold'
    
    cell_style = ParagraphStyle(
        name='CellStyle',
        fontName='Helvetica',
        fontSize=8,
        leading=10,        # Satır aralığı
        alignment=1,       # 0=Sola, 1=Ortala, 2=Sağa
        textColor=colors.black
    )
    
    # Başlık Ekle
    elements.append(Paragraph("2025-2026 Guz Donemi Sinav Programi", title_style))
    elements.append(Spacer(1, 20))
    
    # Tablo Verisi Hazırla
    # Başlıklar
    headers = ['Tarih', 'Saat', 'Ders Kodu', 'Ders Adi', 'Derslik', 'Hoca']
    data = [headers]
    
    # Verileri Sırala (Tarihe göre)
    sorted_schedules = sorted(schedules, key=lambda x: (x.exam_date, x.start_time))
    
    for sch in sorted_schedules:
        # Tarih formatla
        tarih = sch.exam_date.strftime('%d.%m.%Y')
        saat = sch.start_time.strftime('%H:%M')
        
        # Ek sınıflar varsa ekle
        derslik_str = sch.classroom.name
        if sch.additional_classrooms:
            derslik_str += f"\n(+{sch.additional_classrooms})"
            
        hoca_str = sch.teacher.name if sch.teacher else "-"
        ders_adi_str = sch.course.name if sch.course else "-"
        ders_kodu = sch.course.code if sch.course else "-"
        
        # Bu işlem, metin sütuna sığmadığında otomatik olarak alt satıra geçmesini sağlar.
        p_ders_adi = Paragraph(ders_adi_str, cell_style)
        p_hoca = Paragraph(hoca_str, cell_style)
        p_derslik = Paragraph(derslik_str, cell_style)
        
        # Veriyi satır olarak ekle (Paragraph nesneleriyle beraber)
        data.append([tarih, saat, ders_kodu, p_ders_adi, p_derslik, p_hoca])
        
    # Tablo Oluştur
    col_widths = [55, 35, 55, 190, 85, 115]
    
    # repeatRows=1: Tablo başlığının her yeni sayfada tekrar etmesini sağlar
    t = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Tablo Stili
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), # Başlık arka plan rengi
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Başlık yazı rengi
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), # Yatay hizalama
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # YENİ: Dikey hizalama (Metin kaydığında diğerleri ortada kalsın)
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige), # Satır renkleri
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8) # Yazı boyutu
    ]))
    
    elements.append(t)
    
    # PDF'i Oluştur
    doc.build(elements)
    
    return filename

def excel_cikti_al(schedules):
    """
    Sınav programını Excel olarak oluşturur.
    """
    data = []
    # Verileri Sırala
    sorted_schedules = sorted(schedules, key=lambda x: (x.exam_date, x.start_time))
    
    for sch in sorted_schedules:
        data.append({
            'Tarih': sch.exam_date.strftime('%d.%m.%Y'),
            'Saat': sch.start_time.strftime('%H:%M'),
            'Ders Kodu': sch.course.code if sch.course else "-",
            'Ders Adı': sch.course.name if sch.course else "-",
            'Öğrenci Sayısı': sch.course.student_count if sch.course else 0,
            'Derslik': sch.classroom.name + (f" (+{sch.additional_classrooms})" if sch.additional_classrooms else ""),
            'Öğretim Üyesi': sch.teacher.name if sch.teacher else "-"
        })
        
    df = pd.DataFrame(data)
    filename = "sinav_programi.xlsx"
    df.to_excel(filename, index=False)
    
    return filename