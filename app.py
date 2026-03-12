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

# Nagłówek: Logo + Tytuł + Przyciski
col_logo, col_rest = st.columns([1, 4])

with col_logo:
    try:
        st.image("KOD A.png", use_container_width=True)
    except:
        st.write("🖼️")

with col_rest:
    col_title, col_calc, col_new = st.columns([2, 1, 1])
    with col_title:
        st.title("Wycena")
    with col_calc:
        # Przycisk do odświeżania cennika (wymusza pobranie z GitHub)
        if st.button("Odśwież 🔄", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cennik zaktualizowany!") # Małe powiadomienie
    with col_new:
        # Przycisk do nowej wyceny (czyści pole tekstowe)
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

        col1, col2 = st.columns(2)
        szer = col1.number_input("Szerokość (cm)", value=szer_init)
        wys = col2.number_input("Wysokość (cm)", value=wys_init)

        # Dane z cennika
        c_l_netto = float(str(l['cena_l_netto']).replace(',', '.'))
        c_o_netto = float(str(l['cena_o_netto']).replace(',', '.'))
        sz_listwy = float(str(l['szerokosc']).replace(',', '.'))

        # Obliczenia materiałowe
        obwod_m = ((2 * szer) + (2 * wys) + (8 * sz_listwy)) / 100
        pow_m2 = (szer * wys) / 10000

        # Koszty zakupu u producenta (BRUTTO)
        koszt_prod_listwa = (c_l_netto * VAT) * obwod_m
        koszt_prod_oprawa = (c_o_netto * VAT) * obwod_m

        st.info(f"""
        Listwa: {l['kod']} ({sz_listwy} cm) | POTRZEBA: {obwod_m:.2f} mb / {pow_m2:.3f} mkw
        
        KOSZT PROD. (brutto): Listwa {koszt_prod_listwa:.2f} zł / Rama {koszt_prod_oprawa:.2f} zł
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

        # Sekcja usługi ręcznej
        st.divider()
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            dodaj_usluge = st.checkbox("Dodatkowa usługa")
        with col_u2:
            kwota_uslugi = st.number_input("Cena (zł)", value=0.0, step=1.0, label_visibility="collapsed")

        if dodaj_usluge and kwota_uslugi > 0:
            suma += kwota_uslugi
            wybrane_do_akcji.append(f"Usluga dodatkowa: {kwota_uslugi:.2f} zl")

        st.divider()
        st.header(f"RAZEM DO ZAPŁATY: {suma:.2f} zł")

        if suma > 0:
            c1, c2 = st.columns(2)
            tekst_sms = f"Wycena (Listwa {l['kod']}, {int(szer)}x{int(wys)}cm):\n" + "\n".join(wybrane_do_akcji) + f"\nSuma: {suma:.2f} zl\nwww.antyramy.eu"
            
            c1.link_button("📱 Wyślij SMS", f"sms:?body={urllib.parse.quote(tekst_sms)}", use_container_width=True)
            
            try:
                pdf_bytes = create_pdf(l['kod'], szer, wys, obwod_m, pow_m2, wybrane_do_akcji, suma)
                c2.download_button(label="📄 Pobierz PDF", data=pdf_bytes, file_name=f"wycena_{l['kod']}_{int(szer)}x{int(wys)}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e:
                c2.error(f"Błąd PDF: {e}")
                
            st.text_area("Podgląd tekstu do skopiowania:", tekst_sms, height=120)
    else:
        st.error(f"Nie znaleziono kodu: {kod_szukany}")

with st.expander("🛠️ Diagnostyka"):
    if config:
        st.write(f"Marża listwa: {config['marza_listwa']*100}% | Marża oprawa: {config['marza_oprawa']*100}%")
        st.write(f"Cena Float Netto: {config['float']} zł")
