import pandas as pd
import os
import re
from pathlib import Path

# --- MANUEL DERS İSİM LİSTESİ (SABİT VERİ) ---
DERS_ISIMLERI = {
    # Bilgisayar Müh.
    "BLM111": "BİLGİSAYAR MÜHENDİSLİĞİNE GİRİŞ",
    "BLM328": "BİLGİSAYAR MİMARİSİ VE ORGANİZASYONU",
    "BLM331": "ALGORİTMA TASARIMI VE ANALİZİ",
    "MAT110": "MATEMATİK 1",
    "MAT211": "DİFERANSİYEL DENKLEMLER",
    "MAT213": "AYRIK MATEMATİK",
    "MAT220": "SAYISAL YÖNTEMLER",
    "BLM337": "YAPAY ZEKA",
    "BLM215": "TEMEL ELEKTRONİK VE UYGULAMALARI",
    "MSEC006": "KRİPTOLOJİYE GİRİŞ",
    "BLM101": "İŞ SAĞLIĞI VE GÜVENLİĞİ",
    "BLM417": "İŞ SAĞLIĞI VE GÜVENLİĞİ",

    # Yazılım Müh.
    "YZM119": "YAZILIM MÜHENDİSLİĞİNE GİRİŞ",
    "YZM326": "BİLGİSAYAR MİMARİSİ VE ORGANİZASYONU",
    "YZM329": "YAZILIM TEST VE KALİTE",
    "YZM332": "ALGORİTMA TASARIMI VE ANALİZİ",
    "YZM335": "YAPAY ZEKA",
    "YZM219": "YAZILIM GEREKSİNİM ANALİZİ",
    "YZM101": "İŞ SAĞLIĞI VE GÜVENLİĞİ",

    # Ortak / Diğer
    "SEC908": "TÜKETİCİ PSİKOLOJİSİ",
    "SEC130": "İŞ SAĞLIĞI VE GÜVENLİĞİ",
}

def parse_student_list_excel(file_path):
    students = []
    course_code = None
    
    filename = Path(file_path).name
    # Kod Bulma
    match = re.search(r'\[(.*?)\]', filename)
    if match:
        course_code = match.group(1)
    else:
        match_backup = re.search(r'([A-Z]{3}\d{3})', filename)
        if match_backup:
            course_code = match_backup.group(1)
        else:
            course_code = Path(file_path).stem

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, sep=None, engine='python', header=None)
        else:
            df = pd.read_excel(file_path, header=None)

        for index, row in df.iterrows():
            row_vals = [str(x).strip() for x in row.values]
            s_no = None
            s_name = None
            
            for i, val in enumerate(row_vals):
                if re.match(r'^\d{7,15}$', val):
                    s_no = val
                    if i + 1 < len(row_vals):
                        possible_name = row_vals[i+1]
                        if len(possible_name) > 3 and not any(char.isdigit() for char in possible_name):
                            s_name = possible_name
                        elif i + 2 < len(row_vals):
                             next_val = row_vals[i+2]
                             if len(next_val) > 2:
                                 s_name = f"{possible_name} {next_val}"

                    if s_no and s_name and "unnamed" not in s_name.lower():
                        students.append({
                            'student_no': s_no,
                            'name': s_name,
                            'course_code': course_code
                        })
                        break
    except Exception as e:
        print(f"❌ Hata ({filename}): {e}")

    # Manuel listeden ismi çek
    final_name = DERS_ISIMLERI.get(course_code, f"{course_code} Dersi")
    
    return students, course_code, final_name

def parse_capacities(file_path):
    capacities = {}
    try:
        df = pd.read_excel(file_path)
        for idx, row in df.iterrows():
            if len(row) >= 2:
                name = str(row.iloc[0]).strip()
                try:
                    cap = int(row.iloc[1])
                    capacities[name] = cap
                except: continue
    except: pass
    return capacities

def parse_proximity_list(file_path):
    proximity_data = []
    tum_derslikler = set()
    try:
        df = pd.read_excel(file_path)
        for idx, row in df.iterrows():
            cols = [str(c).strip() for c in row.values if pd.notna(c)]
            if len(cols) < 2: continue
            main_room = cols[0]
            tum_derslikler.add(main_room)
            nearby_list = re.split(r'[,;]', cols[1])
            for neighbor in nearby_list:
                neighbor = neighbor.strip()
                if neighbor and neighbor != main_room and len(neighbor) < 20:
                    proximity_data.append({'classroom1': main_room, 'classroom2': neighbor})
                    tum_derslikler.add(neighbor)
    except: pass
    return proximity_data, tum_derslikler

def import_all_data(folder_path):
    all_students = {}
    proximity_data = []
    tum_derslikler = set()
    room_capacities = {}
    
    folder = Path(folder_path)
    cap_files = list(folder.glob("*kapasite*"))
    if cap_files: room_capacities = parse_capacities(str(cap_files[0]))
    
    files = list(folder.glob("SınıfListesi*"))
    print(f"📂 {len(files)} sınıf listesi taranıyor...")
    
    for f in files:
        if f.name.startswith('~'): continue
        
        st, code, name = parse_student_list_excel(str(f))
        
        if st and code:
            if code in all_students:
                # --- MÜKERRER KAYIT KONTROLÜ (YENİ KISIM) ---
                # Mevcut öğrencilerin numaralarını bir kümeye al
                existing_ids = set(s['student_no'] for s in all_students[code]['students'])
                
                added_count = 0
                for student in st:
                    # Eğer bu öğrenci numarası listede YOKSA ekle
                    if student['student_no'] not in existing_ids:
                        all_students[code]['students'].append(student)
                        added_count += 1
                
                print(f"  ➕ {code}: {added_count} YENİ kişi eklendi. (Mükerrer kayıtlar atlandı)")
                
                # İsmi de güncelle
                all_students[code]['name'] = name
            else:
                all_students[code] = {
                    'students': st,
                    'name': name
                }
                print(f"  ✅ {code}: {len(st)} kişi oluşturuldu. (Ders: {name})")
            
    prox_files = list(folder.glob("*Yakınlık*"))
    if prox_files:
        p_data, rooms = parse_proximity_list(str(prox_files[0]))
        proximity_data = p_data
        tum_derslikler.update(rooms)
    
    return all_students, proximity_data, tum_derslikler, room_capacities