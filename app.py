import streamlit as st
import pandas as pd
import re
import urllib.parse

# Stała VAT
VAT = 1.23

# 1. FUNKCJA ŁADOWANIA DANYCH
@st.cache_data(show_spinner="Ładowanie cennika...")
def load_data():
    try:
        # Wczytanie pliku (sep=; decimal=,)
        df_raw = pd.read_csv('cennik.csv', sep=';', decimal=',', header=None, dtype=str)
        
        # Funkcja pomocnicza do stopki
        def get_val_footer(keyword, col_idx):
            mask = df_raw[0].astype(str).str.lower().str.contains(keyword.lower(), na=False)
            rows = df_raw[mask]
            if not rows.empty:
                val = str(rows.iloc[0, col_idx]).replace(',', '.')
                return float(val)
            return 0.0

        # Pobieranie marż i cen dodatków
        prices = {
            'float': get_val_footer('float', 2),
            'hdf': get_val_footer('hdf', 2),
            'antyreflex': get_val_footer('anty', 2),
            'paspartu': get_val_footer('pas', 2),
            'marza_listwa': get_val_footer('mar', 2) / 100 if get_val_footer('mar', 2) > 0 else 0.5,
            'marza_oprawa': get_val_footer('mar', 3) / 100 if get_val_footer('mar', 3) > 0 else 0.3
        }

        # Wyodrębnienie listew (pomijamy 2 wiersze nagłówka)
        df_frames = df_raw.iloc[2:].copy()
        
        # Szukamy początku stopki, aby nie brać jej do listy listew
        stopka_mask = df_frames[0].astype(str).str.lower().str.contains('float|hdf|anty|pas|mar', na=False)
        if stopka_mask.any():
            stopka_idx = stopka_mask.idxmax()
            df_frames = df_frames.loc[:stopka_idx-1]
        
        # Przypisanie kolumn
        df_frames.columns = ['kod', 'ilosc_mb', 'cena_listwa_netto', 'cena_oprawa_netto', 'szerokosc']
        
        # CZYSZCZENIE: Usuwamy spacje i upewniamy się, że kod to tekst
        df_frames['kod'] = df_frames['kod'].astype(str).str.strip()
        
        return df_frames, prices
    except Exception as e:
        st.error(f"Błąd krytyczny pliku CSV: {e}")
        return None, None

# Inicjalizacja
df, config = load_data()

st.set_page_config(page_title="Wycena Antyramy.eu", layout="centered")

# Nagłówek i Reset
c_title, c_reset = st.columns([3, 1])
with c_title:
    st.title("🖩 Kalkulator Wyceny")
with c_reset:
    if st.button("ODŚWIEŻ CENNIK 🔄"):
        st.cache_data.clear()
        st.rerun()

# --- WPISYWANIE ---
input_tekst = st.text_input("Podaj kod i wymiar (np. '3484 50x60'):")

if input_tekst and df is not None:
    # Wyciąganie liczb (kod, szer, wys)
    liczby = re.findall(r'\d+', input_tekst)
    
    if len(liczby) >= 1:
        szukany_kod = liczby[0]
        # Szukamy dokładnie takiego kodu
        wybrana = df[df['kod'] == szukany_kod]
        
        if not wybrana.empty:
            l = wybrana.iloc[0]
            
            # Pobieranie domyślnych wymiarów z tekstu lub standard 30x40
            szer_val = float(liczby[1]) if len(liczby) >= 3 else 30.0
            wys_val = float(liczby[2]) if len(liczby) >= 3 else 40.0
            
            # Pola do poprawki
            col1, col2 = st.columns(2)
            szer = col1.number_input("Szerokość (cm)", value=szer_val)
            wys = col2.number_input("Wysokość (cm)", value=wys_val)

            # Konwersja cen z wiersza
            c_l_netto = float(str(l['cena_listwa_netto']).replace(',', '.'))
            c_o_netto = float(str(l['cena_oprawa_netto']).replace(',', '.'))
            sz_listwy = float(str(l['szerokosc']).replace(',', '.'))

            # Obliczenia
            obwod_m = ((2 * szer) + (2 * wys) + (8 * sz_listwy)) / 100
            pow_m2 = (szer * wys) / 10000

            st.info(f"Listwa: {l['kod']} ({sz_listwy} cm) | potrzeba: {obwod_m:.2f} m / {pow_m2:.3f} mkw")

            # Ceny Brutto
            k_listwa = (c_l_netto * (1 + config['marza_listwa'])) * VAT * obwod_m
            k_oprawa = (c_o_netto * (1 + config['marza_oprawa'])) * VAT * obwod_m
            k_float = (config['float'] * VAT) * pow_m2
            k_anty = (config['antyreflex'] * VAT) * pow_m2
            k_hdf = (config['hdf'] * VAT) * pow_m2
            k_pp = (config['paspartu'] * VAT) * pow_m2

            st.subheader("Wybierz elementy:")
            suma = 0.0
            wybrane_sms = []
            
            opcje = [("Sama listwa", k_listwa), ("Listwa z oprawą", k_oprawa), 
                     ("Szyba Float", k_float), ("Szyba Antyreflex", k_anty), 
                     ("Płyta HDF", k_hdf), ("Passe-partout", k_pp)]

            for nazwa, cena in opcje:
                if st.checkbox(f"{nazwa}: {cena:.2f} zł"):
                    suma += cena
                    wybrane_sms.append(f"- {nazwa}: {cena:.2f} zł")

            st.divider()
            st.header(f"RAZEM: {suma:.2f} zł")

            if suma > 0:
                tekst_sms = f"Wycena (Listwa {l['kod']}, {int(szer)}x{int(wys)}cm):\n" + "\n".join(wybrane_sms) + f"\n\nSuma: {suma:.2f} zł\nwww.antyramy.eu"
                st.link_button("📱 Wyślij SMS", f"sms:?body={urllib.parse.quote(tekst_sms)}", use_container_width=True)
        else:
            st.error(f"Nie znaleziono kodu: {szukany_kod}")

# --- DIAGNOSTYKA (POMOC W RAZIE BŁĘDÓW) ---
with st.expander("🛠️ Diagnostyka (kliknij, jeśli nie widzisz nowej listwy)"):
    if df is not None:
        st.write("Ostatnie 5 listew w pamięci:")
        st.table(df.head(10)) # Pokaże pierwsze 10 pozycji (tam powinny być nowe)
        st.write(f"Załadowane marże: {config['marza_listwa']*100}% / {config['marza_oprawa']*100}%")
    else:
        st.write("Brak danych w pamięci.")
