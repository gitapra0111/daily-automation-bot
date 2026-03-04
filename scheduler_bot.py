import os
import logging
import sqlite3
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# 1. LOAD ENVIRONMENT VARIABLES
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def kirim_pesan_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Gagal mengirim pesan Telegram: {e}")

def kirim_file_telegram(filepath):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as file:
            files = {'document': file}
            payload = {'chat_id': TELEGRAM_CHAT_ID}
            requests.post(url, data=payload, files=files)
    except Exception as e:
        logging.error(f"Gagal mengirim file Telegram: {e}")

# 2. SETUP FOLDER & LOGGING
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "hasil_ekstrak")
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# 3. FUNGSI UTAMA (BOT SCRAPER + PANDAS + SQLITE)
def job():
    logging.info("Bot berjalan mengambil data menggunakan Pandas...")
    
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        
        driver.get("https://the-internet.herokuapp.com/tables")
        wait.until(EC.presence_of_element_located((By.ID, "table1")))

        # --- TAHAP A: DATA WRANGLING DENGAN PANDAS ---
        html_source = driver.page_source
        # Sedot HTML dan langsung ubah jadi DataFrame (Tabel Pandas)
        df = pd.read_html(StringIO(html_source))[0] 
        
        # Bersihkan Data: Hapus kolom 'Action' karena isinya hanya tombol
        if 'Action' in df.columns:
            df = df.drop(columns=['Action'])
            
        driver.quit() # Matikan browser lebih awal karena data sudah di memori

        # --- TAHAP B: INTEGRASI DATABASE (SQLite) ---
        db_path = os.path.join(DATA_DIR, "database_scraping.db")
        conn = sqlite3.connect(db_path)
        # Simpan tabel Pandas langsung ke Database SQL
        df.to_sql("tabel_karyawan", conn, if_exists="append", index=False)
        conn.close()
        logging.info("✅ Data berhasil di-insert ke tabel_karyawan di Database SQLite.")

        # --- TAHAP C: EXPORT KE EXCEL ---
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nama_file = f"laporan_pandas_{waktu_sekarang}.xlsx"
        lokasi_simpan = os.path.join(DATA_DIR, nama_file)
        
        # Simpan ke Excel tanpa menyertakan nomor index baris
        df.to_excel(lokasi_simpan, index=False)
        logging.info(f"✅ Data Excel berhasil dibuat: {nama_file}")

        # --- TAHAP D: KIRIM TELEGRAM ---
        pesan_sukses = f"✅ Laporan Pandas & Database Selesai!\n⏰ Waktu: {waktu_sekarang}\n🗄️ Data tersimpan permanen di SQLite."
        kirim_pesan_telegram(pesan_sukses)
        kirim_file_telegram(lokasi_simpan)

    except Exception as e:
        logging.error(f"Error: {e}")
        kirim_pesan_telegram(f"🚨 ALERT BOS!\nBot Scraper mengalami error:\n{e}")

if __name__ == "__main__":
    job()