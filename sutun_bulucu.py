import pandas as pd
import os
from pathlib import Path

# Data klasörüne bak
folder = Path('data')
print(f"📂 Klasör taranıyor: {folder.absolute()}")

if not folder.exists():
    print("❌ HATA: 'data' klasörü bulunamadı!")
else:
    files = list(folder.glob("*.xls*")) + list(folder.glob("*.csv"))
    print(f"🔎 Toplam {len(files)} dosya bulundu.\n")

    for f in files:
        if f.name.startswith('~'): continue # Geçici dosyaları atla
        print(f"--- Dosya: {f.name} ---")
        try:
            if f.suffix == '.csv':
                df = pd.read_csv(f, sep=None, engine='python')
            else:
                df = pd.read_excel(f)
            
            # Sütunları yazdır
            print(f"📌 SÜTUNLAR: {df.columns.tolist()}")
            
            # İlk satırı yazdır (Örnek veri görmek için)
            if not df.empty:
                print(f"📝 Örnek Veri: {df.iloc[0].values.tolist()}")
            else:
                print("⚠️ Dosya boş!")
                
        except Exception as e:
            print(f"❌ Okuma Hatası: {e}")
        print("-" * 30 + "\n")