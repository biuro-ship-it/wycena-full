import streamlit as st
import pandas as pd
import re
import urllib.parse

# Stała wartość VAT
VAT = 1.23

# Funkcja czyszcząca pamięć podręczną
def clear_cache():
    st.cache_data.clear()

@st.cache_data
def load_data():
    try:
        # Wczytujemy plik CSV
        df_raw = pd.read_csv('cennik.csv', sep=';', decimal=',', header=None)
        
        def get_val_from_footer(keyword, col_idx):
            mask = df_raw[0].astype(str).str.lower().str.strip().str.contains(keyword.lower())
            rows = df_raw[mask]
            if not rows.empty:
                val = rows.iloc[0, col_idx]
                return float(str(val).replace(',', '.'))
            return 0.0

        prices = {
            'float': get_val_from_footer('float', 2),
            'hdf': get_val_from_footer('hdf', 2),
            'antyreflex': get_val_from_footer('anty', 2),
            'paspartu': get_val_from_footer('pas', 2),
            'marza_listwa': get_val_from_footer('mar', 2) / 100,
            'marza_oprawa': get_val_from_footer('mar', 3) / 100
        }

        df_frames = df_raw.iloc[2:].copy()
        stopka_mask = df_frames[0].astype(str).str.lower().str.contains('float|hdf|anty|pas|mar')
        if stopka_mask.any():
            stopka_idx = stopka_mask.idxmax()
            df_frames = df_frames.loc[:stopka_idx-1]
        
        df_frames.columns = ['kod', 'ilosc_mb', 'cena_listwa_netto', 'cena_oprawa_netto', 'szerokosc']
        df_frames['kod'] = df_frames['kod'].astype(str).str.strip()
        
        return df_frames, prices
    except Exception as e:
        st.error(f"Błąd pliku: {e}")
        return None, None

df, config = load_data()

st.set_page_config(page_title="Wycena Antyramy.eu", layout="centered")

c_title, c_reset = st.columns([3, 1])
with c_title:
    st.title("🖩 Kalkulator")
with c_reset:
    if st.button("Nowa / Odśwież 🔁"):
        clear_cache()
        st.rerun()

input_tekst = st.text_input("Kod i wymiar (np. '365 50x50'):")

if input_tekst and df is not None:
    liczby = re.findall(r'\d+', input_tekst)
    kod = liczby[0] if len(liczby) >= 1 else ""
    szer_def = float(liczby[1]) if len(liczby) >= 3 else 30.0
    wys_def = float(liczby[2]) if len(liczby) >= 3 else 40.0

    wybrana = df[df['kod'] == kod]
    
    if not wybrana.empty:
        l = wybrana.iloc[0]
        c_l_netto = float(str(l['cena_listwa_netto']).replace(',', '.'))
        c_o_netto = float(str(l['cena_oprawa_netto']).replace(',', '.'))
        sz_listwy = float(str(l['szerokosc']).replace(',', '.'))

        # WYŚWIETLANIE PÓŁ DO KOREKTY WYMIARÓW
        col1, col2 = st.columns(2)
        szer = col1.number_input("Szerokość (cm)", value=szer_def)
        wys = col2.number_input("Wysokość (cm)", value=wys_def)

        # OBLICZENIA TECHNICZNE
        # Obwód z naddatkiem: (2*szer + 2*wys + 8*szerokosc_listwy) / 100
        obwod_m = ((2 * szer) + (2 * wys) + (8 * sz_listwy)) / 100
        pow_m2 = (szer * wys) / 10000

        # WYŚWIETLENIE INFORMACJI O LISTWIE I ZAPOTRZEBOWANIU (zgodnie z prośbą)
        st.info(f"Listwa: {l['kod']} ({sz_listwy} cm) | potrzeba: {obwod_m:.2f} m / {pow_m2:.3f} mkw")
            
        # OBLICZENIA FINANSOWE
        k_listwa = (c_l_netto * (1 + config['marza_listwa'])) * VAT * obwod_m
        k_oprawa = (c_o_netto * (1 + config['marza_oprawa'])) * VAT * obwod_m
        k_float = (config['float'] * VAT) * pow_m2
        k_anty = (config['antyreflex'] * VAT) * pow_m2
        k_hdf = (config['hdf'] * VAT) * pow_m2
        k_pp = (config['paspartu'] * VAT) * pow_m2

        st.subheader("Wybierz elementy:")
        wybrane_sms = []
        suma = 0.0
        
        items = [
            ("Sama listwa", k_listwa),
            ("Listwa z oprawą", k_oprawa),
            ("Szyba Float", k_float),
            ("Szyba Antyreflex", k_anty),
            ("Płyta HDF", k_hdf),
            ("Passe-partout", k_pp)
        ]

        for nazwa, cena in items:
            if st.checkbox(f"{nazwa}: {cena:.2f} zł"):
                suma += cena
                wybrane_sms.append(f"- {nazwa}: {cena:.2f} zł")
        
        st.divider()
        st.header(f"SUMA: {suma:.2f} zł")

        if suma > 0:
            tekst_sms = (
                f"Wycena oprawy (Listwa {l['kod']})\n"
                f"Wymiary: {int(szer)}x{int(wys)} cm\n"
                f"Elementy:\n" + "\n".join(wybrane_sms) +
                f"\n\nŁączny koszt: {suma:.2f} zł\n"
                f"Dziękujemy! Zapraszamy na www.antyramy.eu"
            )
            
            st.link_button("📱 Wyślij SMS", f"sms:?body={urllib.parse.quote(tekst_sms)}", use_container_width=True)
            st.text_area("Kopiuj do schowka:", tekst_sms, height=150)
            
    else:
        st.error(f"Nie znaleziono kodu: {kod}")

with st.expander("Ustawienia (sprawdź marże)"):
    st.write(f"Marża Listwa: {config['marza_listwa']*100}%")
    st.write(f"Marża Oprawa: {config['marza_oprawa']*100}%")
    st.write(f"Cena Float Netto: {config['float']} zł/m2")
