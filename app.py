import streamlit as st
import pandas as pd
import re
import urllib.parse

# Stała wartość VAT
VAT = 1.23

@st.cache_data
def load_data():
    try:
        # Wczytujemy cały plik
        df_raw = pd.read_csv('cennik.csv', sep=';', decimal=',', header=None)
        
        # 1. Wyciągamy ceny dodatków z końcówki pliku (szukamy słów kluczy w kolumnie 0)
        def get_val(key, col=2):
            try:
                val = df_raw[df_raw[0].astype(str).str.lower().str.contains(key, na=False)].iloc[0, col]
                return float(str(val).replace(',', '.'))
            except:
                return 0.0

        prices = {
            'float': get_val('float'),
            'hdf': get_val('hdf'),
            'antyreflex': get_val('antyreflex'),
            'paspartu': get_val('paspartu'),
            'marza_listwa': get_val('marża', 2) / 100, # np. 50 -> 0.50
            'marza_oprawa': get_val('marża', 3) / 100  # np. 30 -> 0.30
        }

        # 2. Wyciągamy dane o listwach (wiersze od 2 do momentu wystąpienia słowa 'float')
        # Pomijamy pierwsze dwa wiersze nagłówkowe
        df_frames = df_raw.iloc[2:].copy()
        # Odcinamy stopkę (wszystko od wiersza 'float' w dół)
        stopka_idx = df_frames[0].astype(str).str.lower().str.contains('float', na=False).idxmax()
        df_frames = df_frames.loc[:stopka_idx-1]
        
        df_frames.columns = ['kod', 'ilosc_mb', 'cena_listwa_netto', 'cena_oprawa_netto', 'szerokosc']
        df_frames['kod'] = df_frames['kod'].astype(str).str.strip()
        
        return df_frames, prices
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return None, None

def parsuj_glos(tekst):
    liczby = re.findall(r'\d+', tekst)
    reszta = {"kod": None, "szer": 30.0, "wys": 40.0}
    if len(liczby) >= 1: reszta["kod"] = liczby[0]
    if len(liczby) >= 3:
        reszta["szer"] = float(liczby[1])
        reszta["wys"] = float(liczby[2])
    return reszta

# Ładowanie danych
df, config = load_data()

st.set_page_config(page_title="Kalkulator Antyramy.eu", layout="centered")

# Nagłówek i Reset
col_t, col_r = st.columns([3, 1])
with col_t:
    st.title("🖼️ Kalkulator Wyceny")
with col_r:
    if st.button("Nowa wycena 🔁"):
        st.rerun()

input_tekst = st.text_input("Wpisz kod i wymiar (np. '220 rama 40x50'):")

if input_tekst and df is not None:
    dane = parsuj_glos(input_tekst)
    wybrana = df[df['kod'] == dane["kod"]]
    
    if not wybrana.empty:
        l = wybrana.iloc[0]
        st.success(f"Wybrano listwę: {l['kod']} (szerokość {l['szerokosc']} cm)")
        
        c1, c2 = st.columns(2)
        szer = c1.number_input("Szerokość (cm)", value=dane["szer"])
        wys = c2.number_input("Wysokość (cm)", value=dane["wys"])
            
        # OBLICZENIA LOGICZNE
        obwod_m = ((2 * szer) + (2 * wys) + (8 * float(str(l['szerokosc']).replace(',', '.')))) / 100
        pow_m2 = (szer * wys) / 10000
        
        # Funkcja pomocnicza: (Cena Netto + Marża) + VAT
        def calc_brutto_listwa(netto_prod, marza_procent):
            cena_z_marza = float(str(netto_prod).replace(',', '.')) * (1 + marza_procent)
            return cena_z_marza * VAT * obwod_m

        # Funkcja pomocnicza dla szkła: Netto + VAT
        def calc_brutto_dodatki(netto_m2):
            return netto_m2 * VAT * pow_m2

        opcje = {
            "Sama listwa (brutto)": calc_brutto_listwa(l['cena_listwa_netto'], config['marza_listwa']),
            "Listwa w oprawie (brutto)": calc_brutto_listwa(l['cena_oprawa_netto'], config['marza_oprawa']),
            "Szyba Float": calc_brutto_dodatki(config['float']),
            "Szyba Antyreflex": calc_brutto_dodatki(config['antyreflex']),
            "Płyta HDF": calc_brutto_dodatki(config['hdf']),
            "Passe-partout": calc_brutto_dodatki(config['paspartu'])
        }
        
        st.subheader("Wybierz elementy do wyceny:")
        wybrane_do_sms = []
        suma_brutto = 0.0
        
        for nazwa, cena in opcje.items():
            if st.checkbox(f"{nazwa}: {cena:.2f} zł"):
                suma_brutto += cena
                wybrane_do_sms.append(f"- {nazwa}: {cena:.2f} zł")
        
        st.divider()
        st.header(f"RAZEM BRUTTO: {suma_brutto:.2f} zł")

        if suma_brutto > 0:
            # TREŚĆ WIADOMOŚCI
            tekst_sms = (
                f"Dzień dobry! Dziękujemy za zapytanie o wycenę oprawy.\n"
                f"Poniżej przesyłamy szczegóły kalkulacji:\n\n"
                f"Model: Listwa {l['kod']}\n"
                f"Wymiary: {int(szer)} x {int(wys)} cm\n"
                f"Specyfikacja:\n"
            )
            tekst_sms += "\n".join(wybrane_do_sms)
            tekst_sms += f"\n\nŁączny koszt brutto: {suma_brutto:.2f} zł\n\n"
            tekst_sms += "Dziękujemy za zapytanie o wycenę ramy, zapraszamy również na stronę www.antyramy.eu"
            
            st.subheader("Wyślij wycenę do klienta:")
            
            wiadomosc_url = urllib.parse.quote(tekst_sms)
            st.link_button("📱 Wyślij SMS (Otwórz wiadomości)", f"sms:?body={wiadomosc_url}", use_container_width=True)
            
            st.text_area("Podgląd treści (można skopiować):", tekst_sms, height=250)
            
    else:
        st.error(f"Nie znaleziono kodu: {dane['kod']}")

st.caption("Dane cenowe i marże pobierane automatycznie z cennika.")
