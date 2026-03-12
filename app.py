import streamlit as st
import pandas as pd
import re
import urllib.parse
from fpdf import FPDF

# --- KONFIGURACJA ---
VAT = 1.23

def clean_pl(text):
    """Usuwa polskie znaki dla potrzeb generatora PDF"""
    pl_map = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    return str(text).translate(pl_map)

@st.cache_data(show_spinner="Pobieranie cennika...")
def load_data():
    try:
        # Wczytujemy cennik z GitHub
        df_raw = pd.read_csv('cennik.csv', sep=';', decimal=',', header=None, dtype=str)
        
        def get_val_footer(keyword, col_idx):
            mask = df_raw[0].astype(str).str.lower().str.strip().str.contains(keyword.lower(), na=False)
            rows = df_raw[mask]
            if not rows.empty:
                val = str(rows.iloc[0, col_idx]).replace(',', '.')
                return float(val)
            return 0.0

        prices = {
            'float': get_val_footer('float', 2),
            'hdf': get_val_footer('hdf', 2),
            'antyreflex': get_val_footer('anty', 2),
            'paspartu': get_val_footer('pas', 2),
            'marza_listwa': get_val_footer('mar', 2) / 100 if get_val_footer('mar', 2) > 0 else 0.5,
            'marza_oprawa': get_val_footer('mar', 3) / 100 if get_val_footer('mar', 3) > 0 else 0.3
        }

        df_frames = df_raw.iloc[2:].copy()
        stopka_mask = df_frames[0].astype(str).str.lower().str.contains('float|hdf|anty|pas|mar', na=False)
        if stopka_mask.any():
            stopka_idx = stopka_mask.idxmax()
            df_frames = df_frames.loc[:stopka_idx-1]
        
        df_frames.columns = ['kod', 'ilosc_mb', 'cena_l_netto', 'cena_o_netto', 'szerokosc']
        df_frames['kod'] = df_frames['kod'].astype(str).str.strip()
        
        return df_frames, prices
    except Exception as e:
        st.error(f"Błąd pliku CSV: {e}")
        return None, None

def create_pdf(kod, szer, wys, obwod, mkw, elementy, suma):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, clean_pl("WYCENA OPRAWY - ANTYRAMY.EU"), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, clean_pl(f"Kod listwy: {kod}"), ln=True)
    pdf.cell(0, 10, clean_pl(f"Wymiary obrazu: {int(szer)} x {int(wys)} cm"), ln=True)
    pdf.cell(0, 10, clean_pl(f"Zapotrzebowanie: {obwod:.2f} mb listwy / {mkw:.3f} mkw powierzchni"), ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, clean_pl("Wybrane elementy wyceny:"), ln=True)
    pdf.set_font("Helvetica", "", 12)
    for el in elementy:
        pdf.cell(0, 10, clean_pl(el), ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, clean_pl(f"SUMA BRUTTO: {suma:.2f} PLN"), ln=True)
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(0, 10, clean_pl("Dziekujemy za zapytanie. Zapraszamy do realizacji zlecenia!\nwww.antyramy.eu"))
    return bytes(pdf.output())

# --- INTERFEJS UŻYTKOWNIKA ---
st.set_page_config(page_title="Kalkulator Antyramy.eu", layout="centered")

df, config = load_data()

# Nagłówek: Logo + Tytuł (CZERWONY) + Przyciski
col_logo, col_rest = st.columns([1, 4])

with col_logo:
    try:
        st.image("KOD A.png", use_container_width=True)
    except:
        st.write("🖼️")

with col_rest:
    col_title, col_calc, col_new = st.columns([2, 1, 1])
    with col_title:
        # ZMIANA: Tytuł w kolorze czerwonym przy użyciu HTML
        st.markdown("<h1 style='color: red; margin: 0;'>Wycena</h1>", unsafe_allow_html=True)
    with col_calc:
        if st.button("Odśwież 🔄", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cennik zaktualizowany!")
    with col_new:
        if st.button("Nowa ✨", use_container_width=True):
            st.session_state["main_input"] = ""
            st.rerun()

# Pole do wpisywania kodu i wymiarów
input_tekst = st.text_input("Podaj kod i wymiar (np. '3484 50x70'):", key="main_input")

if input_tekst and df is not None:
    liczby = re.findall(r'\d+', input_tekst)
    kod_szukany = liczby[0] if len(liczby) >= 1 else ""
    
    wybrana = df[df['kod'] == kod_szukany]
    
    if not wybrana.empty:
        l = wybrana.iloc[0]
        szer_init = float(liczby[1]) if len(liczby) >= 3 else 30.0
        wys_init = float(liczby[2]) if len(liczby) >= 3 else 40.0
