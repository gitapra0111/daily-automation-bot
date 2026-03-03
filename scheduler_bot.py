import os
import openpyxl
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv # Library baru untuk membaca .env
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES (Buka gembok rahasia)
# ==========================================
# Membaca token dari file .env agar aman dari hacker
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

# ==========================================
# 2. SETUP FOLDER & LOGGING
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "hasil_ekstrak")
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, "bot_activity.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

# ==========================================
# 3. FUNGSI UTAMA (BOT SCRAPER)
# ==========================================
def job():
    logging.info("Bot Cloud berjalan mengambil data...")
    
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        # Tambahan khusus server linux GitHub
        options.add_argument("--disable-dev-shm-usage") 

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )
        wait = WebDriverWait(driver, 20)
        
        driver.get("https://the-internet.herokuapp.com/tables")
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        workbook = openpyxl.Workbook()
        sheet = workbook.active

        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            data = [col.text for col in cols]
            if data:
                sheet.append(data)

        waktu_sekarang = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nama_file = f"auto_data_{waktu_sekarang}.xlsx"
        lokasi_simpan = os.path.join(DATA_DIR, nama_file)

        workbook.save(lokasi_simpan)
        driver.quit()
        
        logging.info(f"Data Excel berhasil disimpan: {nama_file}")

        logging.info("Mengirim laporan ke Telegram...")
        pesan_sukses = f"✅ Laporan Ekstrak Data dari Server Cloud Selesai!\n⏰ Waktu: {waktu_sekarang}\n📁 File terlampir di bawah ini."
        
        kirim_pesan_telegram(pesan_sukses)
        kirim_file_telegram(lokasi_simpan)
        logging.info("Laporan dan File berhasil dikirim ke HP Bos!\n")

    except Exception as e:
        error_msg = f"❌ Terjadi error saat mengeksekusi bot:\n{e}"
        logging.error(error_msg)
        kirim_pesan_telegram(f"🚨 ALERT BOS!\nBot Scraper di Cloud mengalami error:\n{e}")

# ==========================================
# 4. EKSEKUSI LANGSUNG (Tanpa Loop/Schedule)
# ==========================================
if __name__ == "__main__":
    job()