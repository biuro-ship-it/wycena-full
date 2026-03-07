import streamlit as st
import pandas as pd

# --- KONFIGURACJA CEN SZKŁA I HDF (za m2) ---
# Jeśli te ceny pojawią się w przyszłości w CSV, można je stamtąd pobierać.
# Na ten moment ustawiam stawki przykładowe, które możesz edytować poniżej:
CENA_FLOAT_M2 = 90.0
CENA_ANTYREFLEX_M2 = 180.0
CENA_HDF_M2 = 40.0
CENA_PASSEPARTOUT_M2 = 70.0

# Funkcja do wczytywania i czyszczenia danych
@st.cache_data
def load_data():
    # Wczytujemy plik, pomijając pierwsze dwa wiersze nagłówkowe
    # separator to ';', a decimal to ','
    df = pd.read_csv('cennik.csv', sep=';', decimal=',', skiprows=2, header=None)
    # Nazwy kolumn dla ułatwienia pracy z kodem
    df.columns = ['kod', 'ilosc_mb', 'cena_listwa', 'cena_rama', 'szerokosc']
    # Konwersja kodu na string, żeby ułatwić wyszukiwanie
    df['kod'] = df['kod'].astype(str).str.strip()
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Błąd podczas ładowania pliku CSV: {e}")
    st.stop()

st.set_page_config(page_title="Kalkulator Ramiarski", layout="centered")

st.title("🖼️ System Wyceny Oprawy")
st.write("Wpisz kod lub użyj mikrofonu na klawiaturze telefonu.")

# 1. WYSZUKIWANIE LISTWY
szukany_kod = st.text_input("Kod listwy:", placeholder="np. 34")

if szukany_kod:
    # Szukanie w kolumnie 'kod'
    wybrana_listwa = df[df['kod'] == szukany_kod.strip()]
    
    if not wybrana_listwa.empty:
        l = wybrana_listwa.iloc[0]
        
        st.success(f"Wybrano: {l['kod']} | Szerokość listwy: {l['szerokosc']} cm")
        
        # 2. WYMIARY OBRAZU
        col1, col2 = st.columns(2)
        with col1:
            szer = st.number_input("Szerokość obrazu (cm)", min_value=1.0, value=30.0, step=0.1)
        with col2:
            wys = st.number_input("Wysokość obrazu (cm)", min_value=1.0, value=40.0, step=0.1)
            
        # 3. OBLICZENIA LOGICZNE
        # Obwód z naddatkiem na 4 rogi (każdy róg to 2x szerokość listwy)
        # Formuła: (2*szer + 2*wys + 8*szerokosc_listwy) / 100 (zamiana na metry)
        dlugosc_listwy_m = ((2 * szer) + (2 * wys) + (8 * l['szerokosc'])) / 100
        
        # Powierzchnia w m2 (szer * wys / 10000)
        powierzchnia_m2 = (szer * wys) / 10000
        
        # Wyliczenie poszczególnych kwot
        koszt_listwa = dlugosc_listwy_m * l['cena_listwa']
        koszt_oprawa = dlugosc_listwy_m * l['cena_rama']
        koszt_float = powierzchnia_m2 * CENA_FLOAT_M2
        koszt_anty = powierzchnia_m2 * CENA_ANTYREFLEX_M2
        koszt_hdf = powierzchnia_m2 * CENA_HDF_M2
        koszt_pp = powierzchnia_m2 * CENA_PASSEPARTOUT_M2
        
        st.subheader("Wybierz elementy do podsumowania:")
        
        # 4. POLA WYBORU (CHECKBOXY)
        suma_wyceny = 0.0
        
        c1 = st.checkbox(f"1. Sama listwa ({koszt_listwa:.2f} zł)")
        c2 = st.checkbox(f"2. Listwa z oprawą ({koszt_oprawa:.2f} zł)")
        c3 = st.checkbox(f"3. Szyba Float ({koszt_float:.2f} zł)")
        c4 = st.checkbox(f"4. Szyba Antyreflex ({koszt_anty:.2f} zł)")
        c5 = st.checkbox(f"5. HDF ({koszt_hdf:.2f} zł)")
        c6 = st.checkbox(f"6. Passepartout ({koszt_pp:.2f} zł)")
        
        # Sumowanie zaznaczonych elementów
        if c1: suma_wyceny += koszt_listwa
        if c2: suma_wyceny += koszt_oprawa
        if c3: suma_wyceny += koszt_float
        if c4: suma_wyceny += koszt_anty
        if c5: suma_wyceny += koszt_hdf
        if c6: suma_wyceny += koszt_pp
        
        # 5. WYNIK KOŃCOWY
        st.markdown("---")
        st.markdown(f"### 💰 Razem do zapłaty: **{suma_wyceny:.2f} zł**")
        
    else:
        st.error(f"Nie znaleziono listwy o kodzie: {szukany_kod}")

# Stopka z informacją techniczną
st.caption("Aplikacja korzysta z cennika zapisanego w pliku cennik.csv")
