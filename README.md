# Üniversite Sınav Programı Hazırlama Uygulaması

Bu proje, KOSTÜ (Kocaeli Üniversitesi) için geliştirilmiş bir sınav programı hazırlama ve yönetim sistemidir.

## Özellikler

### Kullanıcı Rolleri
- **Yönetici**: Tüm sistemi yönetir, genel planlamayı başlatır
- **Bölüm/Program Yetkilisi**: Kendi bölümüne ait dersleri ve özel durumları sisteme girer
- **Öğretim Üyeleri**: Planlama sonucunu görüntüleyebilir
- **Öğrenciler**: Planlama sonucunu görüntüleyebilir

### Ana Özellikler
1. **Ders Yönetimi**: Ders ekleme, silme, güncelleme
2. **Derslik Yönetimi**: Derslik kapasiteleri ve yakınlık bilgileri
3. **Özel Durum Girişi**: 
   - Hoca müsaitlik durumları
   - Özel sınav süreleri (4, 6, 8 saat)
   - Özel derslik atamaları (Lab, Dekanlık vb.)
4. **Otomatik Planlama**: Backtracking algoritması ile kısıt tabanlı planlama
5. **Raporlama**: PDF ve Excel formatında çıktı alma

## Kurulum

### Gereksinimler
- Python 3.8+
- pip

### Adımlar

1. Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

2. Uygulamayı çalıştırın:
```bash
python ana.py
```

3. Tarayıcınızda şu adrese gidin:
```
http://localhost:5000
```

### Varsayılan Giriş Bilgileri
- **Kullanıcı Adı**: admin
- **Şifre**: admin123

## Kullanım

### 1. PDF Verilerini Yükleme
- Yönetici panelinden "PDF'lerden Veri Yükle" butonuna tıklayın
- Sistem, `Yeni klasör` dizinindeki PDF dosyalarını otomatik olarak parse eder:
  - `SnfListesi*.pdf`: Öğrenci listeleri
  - `DerslikYaknlk.pdf`: Derslik yakınlık bilgileri

### 2. Fakülte ve Bölüm Ekleme
- Yönetici panelinden Fakülteler ve Bölümler/Programlar menülerini kullanın

### 3. Ders Ekleme
- Dersler menüsünden yeni ders ekleyin
- Ders kodunu, adını, bölümünü, öğretim üyesini ve sınav bilgilerini girin

### 4. Derslik Ekleme
- Derslikler menüsünden yeni derslik ekleyin
- Derslik adı, kapasitesi ve uygunluk durumunu belirtin

### 5. Otomatik Planlama
- Yönetici veya Bölüm Yetkilisi panelinden "Planla" butonuna tıklayın
- Sistem, tüm kısıtlamalara uygun bir sınav programı oluşturur

### 6. Program Görüntüleme ve Çıktı
- Sınav Programı menüsünden planlamayı görüntüleyin
- PDF veya Excel formatında indirin

## Kısıtlamalar

Sistem aşağıdaki kısıtlamalara uyar:
- Bir ders için birden fazla sınav saati atanamaz
- Bir derslikte aynı anda birden fazla sınav yapılamaz
- Bir öğrencinin aynı saatte iki sınavı olamaz
- Derslik kapasitesi yetersizse yakın dersliklere atama yapılır
- Hoca yalnızca müsait olduğu günlerde sınava girebilir
- Belirtilen sınav süresi dışında planlama yapılamaz

## Teknik Detaylar

- **Backend**: Flask (Python)
- **Veritabanı**: SQLite
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Planlama Algoritması**: Backtracking (kısıt tabanlı)
- **Çıktı**: ReportLab (PDF), OpenPyXL (Excel)

## Dosya Yapısı

```
.
├── ana.py                  # Flask ana uygulama
├── modeller.py             # Veritabanı modelleri
├── pdf_ayiklayici.py       # PDF parse modülü
├── planlama_algoritmasi.py # Otomatik planlama algoritması
├── cikti_araclari.py       # PDF/Excel export modülleri
├── requirements.txt        # Python bağımlılıkları
├── templates/             # HTML template'leri
│   ├── base.html
│   ├── login.html
│   ├── admin_dashboard.html
│   └── ...
└── Yeni klasör/           # PDF dosyaları
    ├── SnfListesi*.pdf
    └── DerslikYaknlk.pdf
```

## Geliştirme Notları

- Veritabanı otomatik olarak `sinav_programi.db` adıyla oluşturulur
- İlk çalıştırmada varsayılan admin kullanıcısı oluşturulur
- PDF parse işlemi Türkçe karakterleri destekler
- Planlama algoritması öğrenci sayısına göre dersleri önceliklendirir

## Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
