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
        df_raw = pd.read_csv('cennik.csv', sep=';', decimal=',', header=None, dtype=str)
        
        def get_val_footer(keyword, col_idx):
            mask = df_raw[0].astype(str).str.lower().str.strip().str.contains(keyword.lower(), na=False)
            rows = df_raw[mask]
            if not rows.empty:
                val = str(rows.iloc[0, col_idx]).replace(',', '.')
                try: return float(val)
                except: return 0.0
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

# --- START UI ---
st.set_page_config(page_title="Kalkulator Antyramy.eu", layout="centered")

df, config = load_data()

# Nagłówek: Tytuł (Czerwony) + Przyciski
col_title, col_calc, col_new = st.columns([2, 1, 1])
with col_title:
    st.markdown("<h1 style='color: red; margin: 0; padding: 0;'>Wycena</h1>", unsafe_allow_html=True)
with col_calc:
    if st.button("Odśwież 🔄", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_new:
    if st.button("Nowa ✨", use_container_width=True):
        st.rerun() # Przycisk przeładowuje stronę do ustawień domyślnych

# --- WPISYWANIE DANYCH ---
if df is not None:
    # 1. Wybór kodu listwy
    lista_kodow = sorted(df['kod'].unique().tolist())
    wybrany_kod = st.selectbox("Wybierz kod listwy:", lista_kodow)
    
    # 2. Pola Szerokość x Wysokość obok siebie
    c_s, c_x, c_w = st.columns([10, 1, 10])
    with c_s:
        szer = st.number_input("Szerokość (cm)", value=30.0, step=0.1)
    with c_x:
        st.markdown("<h3 style='text-align: center; padding-top: 30px;'>x</h3>", unsafe_allow_html=True)
    with c_w:
        wys = st.number_input("Wysokość (cm)", value=40.0, step=0.1)

    # Pobranie danych wybranej listwy
    l = df[df['kod'] == wybrany_kod].iloc[0]
    
    st.divider()

    # Dane z cennika
    c_l_netto = float(str(l['cena_l_netto']).replace(',', '.'))
    c_o_netto = float(str(l['cena_o_netto']).replace(',', '.'))
    sz_listwy = float(str(l['szerokosc']).replace(',', '.'))

    # Obliczenia
    obwod_m = ((2 * szer) + (2 * wys) + (8 * sz_listwy)) / 100
    pow_m2 = (szer * wys) / 10000

    st.info(f"""
    Listwa: **{wybrany_kod}** ({sz_listwy} cm) | POTRZEBA: **{obwod_m:.2f} mb** / **{pow_m2:.3f} mkw**
    
    KOSZT PROD. (brutto): Listwa {((c_l_netto * VAT) * obwod_m):.2f} zł / Rama {((c_o_netto * VAT) * obwod_m):.2f} zł
    """)

    # Obliczenia dla klienta
    k_listwa = (c_l_netto * (1 + config['marza_listwa'])) * VAT * obwod_m
    k_oprawa = (c_o_netto * (1 + config['marza_oprawa'])) * VAT * obwod_m
    k_float = (config['float'] * VAT) * pow_m2
    k_anty = (config['antyreflex'] * VAT) * pow_m2
    k_hdf = (config['hdf'] * VAT) * pow_m2
    k_pp = (config['paspartu'] * VAT) * pow_m2

    st.subheader("Wybierz elementy:")
    suma = 0.0
    wybrane_do_akcji = []
    
    opcje = [("Sama listwa", k_listwa), ("Listwa z oprawą", k_oprawa), 
                ("Szyba Float", k_float), ("Szyba Antyreflex", k_anty), 
                ("Płyta HDF", k_hdf), ("Passe-partout", k_pp)]

    for nazwa, cena in opcje:
        if st.checkbox(f"{nazwa}: {cena:.2f} zł"):
            suma += cena
            wybrane_do_akcji.append(f"{nazwa}: {cena:.2f} zl")

    st.divider()
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        dodaj_usluge = st.checkbox("Dodatkowa usługa")
    with col_u2:
        kwota_uslugi = st.number_input("Cena (zł)", value=0.0, step=1.0)

    if dodaj_usluge and kwota_uslugi > 0:
        suma += kwota_uslugi
        wybrane_do_akcji.append(f"Usluga dodatkowa: {kwota_uslugi:.2f} zl")

    st.divider()
    st.markdown(f"### RAZEM DO ZAPŁATY: {suma:.2f} zł")

    if suma > 0:
        c1, c2 = st.columns(2)
        t_sms = f"Wycena (Listwa {wybrany_kod}, {int(szer)}x{int(wys)}cm):\n" + "\n".join(wybrane_do_akcji) + f"\nSuma: {suma:.2f} zl\nwww.antyramy.eu"
        c1.link_button("📱 Wyślij SMS", f"sms:?body={urllib.parse.quote(t_sms)}", use_container_width=True)
        
        try:
            p_bytes = create_pdf(wybrany_kod, szer, wys, obwod_m, pow_m2, wybrane_do_akcji, suma)
            c2.download_button("📄 Pobierz PDF", p_bytes, f"wycena_{wybrany_kod}_{int(szer)}x{int(wys)}.pdf", "application/pdf", use_container_width=True)
        except Exception as e:
            c2.error(f"Błąd PDF: {e}")
        
        st.text_area("Podgląd tekstu:", t_sms, height=120)

with st.expander("🛠️ Diagnostyka"):
    if config:
        st.write(f"Marża L: {config['marza_listwa']*100}% | Marża O: {config['marza_oprawa']*100}%")
