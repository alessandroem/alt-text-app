import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import openai
import pandas as pd
import time
import base64

# Setze hier deinen OpenAI API-Key
openai.api_key = st.secrets["openai_api_key"]

st.title("Alt-Text-Generator für Produktbilder")
st.write("Gib Produktseiten ein (z. B. von Vitra, Muuto etc.), und erhalte automatisch beschriftete Bilder.")

urls_input = st.text_area("🔗 Produkt-URLs eingeben (eine pro Zeile)")

if st.button("Analyse starten"):
    urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
    results = []

    with st.spinner("Analysiere Seiten..."):
        for url in urls:
            try:
                page = requests.get(url, timeout=10)
                soup = BeautifulSoup(page.content, 'html.parser')

                # Produktbeschreibung extrahieren (unterhalb der Headline)
                paragraphs = soup.find_all('p')
                description = " ".join(p.text.strip() for p in paragraphs[:3])  # ggf. anpassen

                # Bild-URLs sammeln
                images = soup.find_all('img')
                for img in images:
                    img_url = img.get('src') or img.get('data-src')
                    if img_url and img_url.startswith("http"):
                        try:
                            response = requests.get(img_url, timeout=10)
                            image = Image.open(BytesIO(response.content))

                            # GPT-4 Vision Alt-Text generieren
                            buffered = BytesIO()
                            image.save(buffered, format="PNG")
                            buffered.seek(0)
                            img_base64 = base64.b64encode(buffered.getvalue()).decode()

                            response = openai.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "Du bist ein professioneller Alt-Text-Generator für Produktbilder."
                                    },
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": f"Analysiere dieses Bild im Kontext der folgenden Produktbeschreibung:\n{description}"},
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                                        ]
                                    }
                                ],
                                max_tokens=100
                            )

                            alt_text = response.choices[0].message.content.strip()

                            results.append({
                                "Produkt-URL": url,
                                "Bild-URL": img_url,
                                "Alt-Text": alt_text
                            })

                            time.sleep(1)  # API rate limit

                        except Exception as e:
                            st.warning(f"Fehler bei Bildanalyse: {e}")
            except Exception as e:
                st.warning(f"Fehler beim Laden der Seite {url}: {e}")

    df = pd.DataFrame(results)
    st.success("Fertig! Vorschau unten:")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV-Datei herunterladen", csv, "alt-texte.csv", "text/csv")
