from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from datetime import datetime
import time

# Konfiguracija
URL = "https://www.bhansa.gov.ba/bs/bhansa/konkursi-za-posao"
EMAIL = "vuk.bojic2023@gmail.com"
SENT_ADS_FILE = "sent_bhansa_ads.txt"
WAIT_TIMEOUT = 30

# Funkcija za slanje emaila
def posalji_email(subject, body, to_email):
    from_email = "vuk.bojic2023@gmail.com"
    from_password = "ftlf cfge ozcp jagd"  # Zamijenite sa vašim App Password za Gmail

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email uspešno poslat!")
    except Exception as e:
        print(f"Greška pri slanju emaila: {e}")

# Funkcija za formatiranje oglasa
def formatiraj_oglas(naslov, datum, link):
    # Formatiranje u HTML
    formatiran_oglas = (
        f"<h3><a href='{link}'>{naslov}</a></h3>"
        f"<p><strong>Datum objave:</strong> {datum}</p>"
        f"<p><a href='{link}'>Pročitaj više</a></p>"
        "<hr>"
    )
    return formatiran_oglas

# Funkcija za normalizaciju oglasa
def normalizuj_oglas(naslov, datum):
    return f"{naslov}|{datum}"

# Funkcija za dobijanje oglasa sa stranice
def get_oglasi():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    
    # Dodatne opcije za izbjegavanje detekcije
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Koristite najnoviju verziju ChromeDriver-a
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Postavite korisnički agent
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        print("Učitavam stranicu...")
        driver.get(URL)
        
        # Čekanje da se stranica potpuno učita
        time.sleep(5)
        
        # Provera da li je stranica učitana
        if "BHANSA" not in driver.title:
            print("Stranica se nije pravilno učitala")
            return []
        
        # Čekamo grid container sa oglasima
        print("Čekam da se učita sadržaj...")
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.grid"))
        )
        
        # Dodatno čekanje za JavaScript sadržaj
        time.sleep(3)
        
        # Parsiranje HTML-a
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        # Pronalaženje grid containera
        grid_container = soup.find('div', class_='grid')
        if not grid_container:
            print("Nije pronađen grid container sa oglasima")
            return []
        
        # Pronalaženje svih oglasa
        oglasi_divovi = grid_container.find_all('div', recursive=False)
        print(f"Pronađeno {len(oglasi_divovi)} oglasa")
        
        # Ekstrakcija podataka
        oglasi = []
        for oglas_div in oglasi_divovi:
            try:
                # Datum objave
                datum_p = oglas_div.find('p')
                datum = datum_p.get_text(strip=True) if datum_p else "Nepoznat datum"
                
                # Naslov i link
                naslov_div = oglas_div.find('div')
                if naslov_div and naslov_div.find('a'):
                    naslov = naslov_div.find('a').get_text(strip=True)
                    link = naslov_div.find('a')['href']
                    link = f"https://www.bhansa.gov.ba{link}" if link.startswith('/') else link
                else:
                    naslov = "Nepoznat naslov"
                    link = "#"
                
                oglasi.append({
                    'naslov': naslov,
                    'datum': datum,
                    'link': link
                })
            except Exception as e:
                print(f"Greška pri obradi oglasa: {e}")
                continue
        
        return oglasi
        
    except Exception as e:
        print(f"Greška pri učitavanju oglasa: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return []

# Funkcija za učitavanje poslatih oglasa iz fajla
def ucitaj_poslate_oglasa():
    if not os.path.exists(SENT_ADS_FILE):
        return set()

    with open(SENT_ADS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Funkcija za čuvanje poslatih oglasa u fajl
def sacuvaj_poslate_oglasa(poslednji_oglasi):
    with open(SENT_ADS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(poslednji_oglasi))

# Glavna funkcija
def main():
    # Provera da li fajl postoji, ako ne, kreiraj ga
    if not os.path.exists(SENT_ADS_FILE):
        with open(SENT_ADS_FILE, "w", encoding="utf-8") as f:
            f.write("")

    poslednji_oglasi = ucitaj_poslate_oglasa()
    oglasi = get_oglasi()

    if not oglasi:
        print("Nije uspelo učitavanje oglasa. Proverite internet konekciju ili pokušajte ponovo kasnije.")
        return

    # Normalizujemo trenutne oglase za poređenje
    trenutni_oglasi_normalizovani = set()
    novi_oglasi = []
    
    for oglas in oglasi:
        oglas_id = normalizuj_oglas(oglas['naslov'], oglas['datum'])
        trenutni_oglasi_normalizovani.add(oglas_id)
        if oglas_id not in poslednji_oglasi:
            novi_oglasi.append(oglas)

    # Pronalaženje novih oglasa
    if novi_oglasi:
        print(f"Pronađeno {len(novi_oglasi)} novih oglasa!")

        # Formatiranje i slanje samo novih oglasa
        body = "<html><body>"
        body += f"<h2>Novi konkursi za posao na BHANSA (ažurirano: {datetime.now().strftime('%d.%m.%Y %H:%M')})</h2><br>"
        
        for oglas in novi_oglasi:
            body += formatiraj_oglas(oglas['naslov'], oglas['datum'], oglas['link'])
        
        body += "<p><small>Ovaj email je automatski generisan. Za prestanak slanja obavijesti, deaktivirajte skriptu.</small></p>"
        body += "</body></html>"

        posalji_email("Novi konkursi za posao u BHANSA", body, EMAIL)

        # Ažuriramo poslednje oglase
        poslednji_oglasi.update(normalizuj_oglas(oglas['naslov'], oglas['datum']) for oglas in novi_oglasi)
        sacuvaj_poslate_oglasa(poslednji_oglasi)
    else:
        print("Nema novih oglasa za posao.")

if __name__ == "__main__":
    main()