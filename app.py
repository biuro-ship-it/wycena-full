import streamlit as st
import pandas as pd
import re

# --- KONFIGURACJA CEN (edytuj wg potrzeb) ---
CENA_FLOAT_M2 = 90.0
CENA_ANTYREFLEX_M2 = 180.0
CENA_HDF_M2 = 40.0
CENA_PASSEPARTOUT_M2 = 70.0

@st.cache_data
def load_data():
    df = pd.read_csv('cennik.csv', sep=';', decimal=',', skiprows=2, header=None)
    df.columns = ['kod', 'ilosc_mb', 'cena_listwa', 'cena_rama', 'szerokosc']
    df['kod'] = df['kod'].astype(str).str.strip()
    return df

# Funkcja do wyciągania liczb z tekstu (np. z "220 rama 40x50")
def parsuj_glos(tekst):
    liczby = re.findall(r'\d+', tekst)
    reszta = {"kod": None, "szer": 30.0, "wys": 40.0}
    if len(liczby) >= 1:
        reszta["kod"] = liczby[0]
    if len(liczby) >= 3:
        reszta["szer"] = float(liczby[1])
        reszta["wys"] = float(liczby[2])
    return reszta

df = load_data()

st.set_page_config(page_title="Kalkulator Ramiarski", layout="centered")
st.title("🖼️ Inteligentna Wycena")

# WEJŚCIE GŁOSOWE / TEKSTOWE
input_tekst = st.text_input("Powiedz kod i wymiary (np. '220 rama 40 na 50'):")

if input_tekst:
    dane = parsuj_glos(input_tekst)
    kod = dane["kod"]
    
    wybrana_listwa = df[df['kod'] == kod]
    
    if not wybrana_listwa.empty:
        l = wybrana_listwa.iloc[0]
        st.success(f"Wybrano listwę: {l['kod']}")
        
        # Automatycznie podstawia wymiary wyciągnięte z głosu
        col1, col2 = st.columns(2)
        with col1:
            szer = st.number_input("Szerokość (cm)", value=dane["szer"])
        with col2:
            wys = st.number_input("Wysokość (cm)", value=dane["wys"])
            
        # OBLICZENIA
        obwod_m = ((2 * szer) + (2 * wys) + (8 * l['szerokosc'])) / 100
        powierzchnia_m2 = (szer * wys) / 10000
        
        k_listwa = obwod_m * l['cena_listwa']
        k_rama = obwod_m * l['cena_rama']
        k_float = powierzchnia_m2 * CENA_FLOAT_M2
        k_anty = powierzchnia_m2 * CENA_ANTYREFLEX_M2
        k_hdf = powierzchnia_m2 * CENA_HDF_M2
        k_pp = powierzchnia_m2 * CENA_PASSEPARTOUT_M2
        
        st.subheader("Wybierz elementy:")
        suma = 0.0
        if st.checkbox(f"Sama listwa ({k_listwa:.2f} zł)"): suma += k_listwa
        if st.checkbox(f"Listwa z oprawą ({k_rama:.2f} zł)"): suma += k_rama
        if st.checkbox(f"Szyba Float ({k_float:.2f} zł)"): suma += k_float
        if st.checkbox(f"Szyba Antyreflex ({k_anty:.2f} zł)"): suma += k_anty
        if st.checkbox(f"HDF ({k_hdf:.2f} zł)"): suma += k_hdf
        if st.checkbox(f"Passepartout ({k_pp:.2f} zł)"): suma += k_pp
        
        st.divider()
        st.header(f"RAZEM: {suma:.2f} zł")
    else:
        st.error(f"Nie znaleziono kodu: {kod}")
