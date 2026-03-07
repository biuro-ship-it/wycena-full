import streamlit as st
import pandas as pd
import re
import urllib.parse

# --- KONFIGURACJA CEN STAŁYCH ---
CENA_FLOAT_M2 = 90.0
CENA_ANTYREFLEX_M2 = 180.0
CENA_HDF_M2 = 40.0
CENA_PASSEPARTOUT_M2 = 70.0

@st.cache_data
def load_data():
    # Wczytywanie Twojego pliku cennik.csv
    try:
        df = pd.read_csv('cennik.csv', sep=';', decimal=',', skiprows=2, header=None)
        df.columns = ['kod', 'ilosc_mb', 'cena_listwa', 'cena_rama', 'szerokosc']
        df['kod'] = df['kod'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Problem z plikiem CSV: {e}")
        return None

def parsuj_glos(tekst):
    liczby = re.findall(r'\d+', tekst)
    reszta = {"kod": None, "szer": 30.0, "wys": 40.0}
    if len(liczby) >= 1: reszta["kod"] = liczby[0]
    if len(liczby) >= 3:
        reszta["szer"] = float(liczby[1])
        reszta["wys"] = float(liczby[2])
    return reszta

# Inicjalizacja danych
df = load_data()

st.set_page_config(page_title="Kalkulator Ramiarski", layout="centered")

# Nagłówek i przycisk resetu
col_t, col_r = st.columns([3, 1])
with col_t:
    st.title("🖼️ Wycena")
with col_r:
    if st.button("Czyść 🔁"):
        st.rerun()

# WEJŚCIE DANYCH
input_tekst = st.text_input("Wpisz/Powiedz (np. '220 rama 40 na 50'):", key="main_input")

if input_tekst and df is not None:
    dane = parsuj_glos(input_tekst)
    wybrana_listwa = df[df['kod'] == dane["kod"]]
    
    if not wybrana_listwa.empty:
        l = wybrana_listwa.iloc[0]
        st.success(f"Listwa: {l['kod']} (szer. {l['szerokosc']} cm)")
        
        c1, c2 = st.columns(2)
        szer = c1.number_input("Szerokość (cm)", value=dane["szer"])
        wys = c2.number_input("Wysokość (cm)", value=dane["wys"])
            
        # OBLICZENIA
        # (2*szer + 2*wys + 8*szerokosc) / 100
        obwod_m = ((2 * szer) + (2 * wys) + (8 * float(l['szerokosc']))) / 100
        pow_m2 = (szer * wys) / 10000
        
        opcje = {
            "Sama listwa": obwod_m * float(l['cena_listwa']),
            "Oprawa komplet": obwod_m * float(l['cena_rama']),
            "Szyba Float": pow_m2 * CENA_FLOAT_M2,
            "Szyba Antyreflex": pow_m2 * CENA_ANTYREFLEX_M2,
            "Płyta HDF": pow_m2 * CENA_HDF_M2,
            "Passe-partout": pow_m2 * CENA_PASSEPARTOUT_M2
        }
        
        st.subheader("Wybierz elementy:")
        wybrane_do_sms = []
        suma = 0.0
        
        for nazwa, cena in opcje.items():
            if st.checkbox(f"{nazwa}: {cena:.2f} zł"):
                suma += cena
                wybrane_do_sms.append(f"- {nazwa}: {cena:.2f} zł")
        
        st.divider()
        st.header(f"RAZEM: {suma:.2f} zł")

        # --- SEKCJA SMS / SCHOWEK ---
        if suma > 0:
            tekst_sms = (
                f"Dzień dobry! Dziękujemy za zapytanie o wycenę oprawy.\n"
                f"Poniżej przesyłamy szczegóły kalkulacji:\n\n"
                f"Model: Listwa {l['kod']} (szer. {l['szerokosc']} cm)\n"
                f"Wymiary: {int(szer)} x {int(wys)} cm\n"
                f"Wybrane elementy:\n"
            )
            
            tekst_sms += "\n".join(wybrane_do_sms)
            tekst_sms += f"\n\nŁączny koszt: {suma:.2f} zł\n\n"
            tekst_sms += "Zapraszamy do realizacji zlecenia oraz na naszą stronę: www.antyramy.eu"
            
            st.subheader("Wyślij lub skopiuj wycenę:")
            
            wiadomosc_url = urllib.parse.quote(tekst_sms)
            st.link_button("📱 Wyślij SMS do klienta", f"sms:?body={wiadomosc_url}", use_container_width=True)
            
            st.text_area("Treść do skopiowania:", tekst_sms, height=250)
            
    else:
        st.error(f"Nie znaleziono kodu: {dane['kod']}")
