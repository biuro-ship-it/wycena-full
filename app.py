# --- SEKCJA SMS / SCHOWEK ---
        if suma > 0:
            # Przygotowanie profesjonalnej treści wiadomości
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
            
            # Przycisk wysyłający bezpośrednio SMS (działa na telefonach)
            wiadomosc_url = urllib.parse.quote(tekst_sms)
            st.link_button("📱 Wyślij SMS do klienta", f"sms:?body={wiadomosc_url}", use_container_width=True)
            
            # Pole tekstowe do kopiowania (np. na Messenger/WhatsApp)
            st.text_area("Treść do skopiowania:", tekst_sms, height=250)
