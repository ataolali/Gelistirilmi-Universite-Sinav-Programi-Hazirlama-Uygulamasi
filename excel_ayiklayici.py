import pandas as pd
import os
import re
from pathlib import Path

def parse_student_list_excel(file_path):
    """
    Excel dosyasındaki öğrenci listesini 'Veri Deseni'ne göre bulur.
    Başlık satırı aramak yerine, doğrudan öğrenci numarası formatına uyan verileri çeker.
    """
    students = []
    course_code = None
    
    # 1. Dosya isminden Ders Kodunu Bul
    filename = Path(file_path).name
    # Köşeli parantez içini dene: SınıfListesi[YZM332]
    match = re.search(r'\[(.*?)\]', filename)
    if match:
        course_code = match.group(1)
    else:
        # Kod başta mı? BLM111...
        match_backup = re.search(r'([A-Z]{3}\d{3})', filename)
        if match_backup:
            course_code = match_backup.group(1)
        else:
            course_code = Path(file_path).stem

    try:
        # Dosyayı "header" yokmuş gibi tamamen oku
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, sep=None, engine='python', header=None)
        else:
            df = pd.read_excel(file_path, header=None)

        # Tüm hücreleri gez ve Öğrenci Numarası bulmaya çalış
        # Kocaeli Üni öğrenci no formatı genelde 9-10 haneli sayılardır
        
        for index, row in df.iterrows():
            row_vals = [str(x).strip() for x in row.values]
            
            # Satırdaki her hücreye bak
            found_student = False
            s_no = None
            s_name = None
            
            for i, val in enumerate(row_vals):
                # Öğrenci No Tespit Etme (Regex: Sadece rakamlardan oluşsun ve en az 7 haneli olsun)
                if re.match(r'^\d{7,15}$', val):
                    s_no = val
                    
                    # İsim genelde numaradan sonraki sütundadır (veya bir sonrakinde)
                    # O yüzden i+1 ve i+2'ye bakıyoruz
                    if i + 1 < len(row_vals):
                        possible_name = row_vals[i+1]
                        # İsim en az 3 harfli olmalı ve içinde sayı olmamalı
                        if len(possible_name) > 3 and not any(char.isdigit() for char in possible_name):
                            s_name = possible_name
                        # Belki Ad ve Soyad ayrı sütunlardadır?
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
                        found_student = True
                        break # Bu satırda öğrenciyi bulduk, diğer sütunlara bakmaya gerek yok
            
    except Exception as e:
        print(f"❌ Hata ({filename}): {e}")

    return students, course_code

def parse_capacities(file_path):
    """
    Derslik kapasitelerini okur.
    Beklenen Format: Sütun 1: Derslik Adı, Sütun 2: Kapasite
    """
    capacities = {}
    try:
        df = pd.read_excel(file_path)
        # Sütun isimlerini umursama, ilk sütun isim, ikinci sütun kapasite varsay
        for idx, row in df.iterrows():
            if len(row) >= 2:
                name = str(row.iloc[0]).strip()
                try:
                    cap = int(row.iloc[1])
                    capacities[name] = cap
                except:
                    continue
    except Exception as e:
        print(f"❌ Kapasite okuma hatası: {e}")
    return capacities

def parse_proximity_list(file_path):
    """
    Yakınlık dosyasını okur.
    Format: M101 | S101,M201...
    """
    proximity_data = []
    tum_derslikler = set()
    
    try:
        df = pd.read_excel(file_path)
        # Hangi sütun ne? İçeriğe bakarak karar verelim
        
        for idx, row in df.iterrows():
            # Satırdaki string olan sütunları al
            cols = [str(c).strip() for c in row.values if pd.notna(c)]
            
            if len(cols) < 2: continue
            
            # İlk sütun Ana Derslik
            main_room = cols[0]
            tum_derslikler.add(main_room)
            
            # İkinci sütun (veya diğerleri) yakınlar
            # "S101, M201, M301" gibi virgüllü olabilir
            nearby_text = cols[1]
            nearby_list = re.split(r'[,;]', nearby_text)
            
            for neighbor in nearby_list:
                neighbor = neighbor.strip()
                if neighbor and neighbor != main_room and len(neighbor) < 20: # Saçma uzunluktaki verileri ele
                    proximity_data.append({
                        'classroom1': main_room,
                        'classroom2': neighbor,
                        'proximity': True
                    })
                    tum_derslikler.add(neighbor)

    except Exception as e:
        print(f"❌ Yakınlık okuma hatası: {e}")
        
    return proximity_data, tum_derslikler

def import_all_data(folder_path):
    """Tüm verileri yöneten ana fonksiyon"""
    all_students = {}
    proximity_data = []
    tum_derslikler = set()
    room_capacities = {}
    
    folder = Path(folder_path)
    
    # 1. Kapasiteleri Oku
    cap_files = list(folder.glob("*kapasite*"))
    if cap_files:
        print(f"📦 Kapasite dosyası okunuyor: {cap_files[0].name}")
        room_capacities = parse_capacities(str(cap_files[0]))
    
    # 2. Sınıf Listelerini Oku
    files = list(folder.glob("SınıfListesi*"))
    print(f"📂 {len(files)} adet sınıf listesi taranıyor...")
    
    for f in files:
        if f.name.startswith('~'): continue
        st, code = parse_student_list_excel(str(f))
        if st:
            all_students[code] = st
            print(f"  ✅ {code}: {len(st)} öğrenci.")
        else:
            print(f"  ⚠️ {code}: Öğrenci bulunamadı!")
            
    # 3. Yakınlıkları Oku
    prox_files = list(folder.glob("*Yakınlık*"))
    if prox_files:
        print(f"📍 Yakınlık dosyası okunuyor...")
        p_data, rooms = parse_proximity_list(str(prox_files[0]))
        proximity_data = p_data
        tum_derslikler.update(rooms)
    
    return all_students, proximity_data, tum_derslikler, room_capacities