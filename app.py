import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import openai
import pandas as pd
import time
import base64

openai.api_key = st.secrets["openai_api_key"]

st.title("Alt-Text-Generator für Produktbilder")
st.write("Gib Produktseiten ein (z. B. von Vitra, Muuto etc.), und erhalte automatisch beschriftete Bilder und Übersetzungen.")

urls_input = st.text_area("🔗 Produkt-URLs eingeben (eine pro Zeile)")

def translate_text(text, target_language):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"Du bist ein professioneller Übersetzer. Übersetze ins {target_language} in präziser, natürlicher Sprache. Maximal 150 Zeichen."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Übersetzungsfehler: {e}"

if st.button("Analyse starten"):
    urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
    results = []

    with st.spinner("Analysiere Seiten..."):
        for url in urls:
            try:
                page = requests.get(url, timeout=10)
                soup = BeautifulSoup(page.content, 'html.parser')
                paragraphs = soup.find_all('p')
                description = " ".join(p.text.strip() for p in paragraphs[:3])

                images = soup.find_all('img')
                for img in images:
                    img_url = img.get('src') or img.get('data-src')
                    if img_url and img_url.startswith("http"):
                        try:
                            response = requests.get(img_url, timeout=10)
                            image = Image.open(BytesIO(response.content))

                            # Bild verkleinern für Vorschau
                            preview_image = image.copy()
                            preview_image.thumbnail((300, 300))
                            buffered = BytesIO()
                            preview_image.save(buffered, format="PNG")
                            preview_base64 = base64.b64encode(buffered.getvalue()).decode()
                            preview_html = f'<img src="data:image/png;base64,{preview_base64}">'

                            # Originalbild codieren für Vision
                            buffered_full = BytesIO()
                            image.save(buffered_full, format="PNG")
                            buffered_full.seek(0)
                            img_base64 = base64.b64encode(buffered_full.getvalue()).decode()

                            response = openai.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "Du bist ein professioneller Alt-Text-Generator. Beschreibung: 80–125 Zeichen, maximal 150 Zeichen."
                                    },
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": f"Erstelle einen Alt-Text für dieses Bild im Kontext der folgenden Produktbeschreibung. Die Länge soll zwischen 80–125 Zeichen liegen, maximal 150 Zeichen:\n{description}"},
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                                        ]
                                    }
                                ],
                                max_tokens=150
                            )

                            alt_text = response.choices[0].message.content.strip()
                            translations = {
                                "DE": translate_text(alt_text, "Deutsch"),
                                "EN": translate_text(alt_text, "Englisch"),
                                "FR": translate_text(alt_text, "Französisch"),
                                "ES": translate_text(alt_text, "Spanisch"),
                                "IT": translate_text(alt_text, "Italienisch"),
                                "NL": translate_text(alt_text, "Niederländisch")
                            }

                            results.append({
                                "Produkt-URL": url,
                                "Bild-URL": img_url,
                                "Bild-Vorschau": preview_html,
                                "Alt-Text (Original)": alt_text,
                                "Alt-Text (DE)": translations["DE"],
                                "Alt-Text (EN)": translations["EN"],
                                "Alt-Text (FR)": translations["FR"],
                                "Alt-Text (ES)": translations["ES"],
                                "Alt-Text (IT)": translations["IT"],
                                "Alt-Text (NL)": translations["NL"]
                            })

                            time.sleep(1)
                        except Exception as e:
                            st.warning(f"Fehler bei Bildanalyse: {e}")
            except Exception as e:
                st.warning(f"Fehler beim Laden der Seite {url}: {e}")

    df = pd.DataFrame(results)
    st.success("Fertig! Vorschau unten:")
    st.write(df.to_html(escape=False), unsafe_allow_html=True)

    csv = df.drop(columns=["Bild-Vorschau"]).to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV-Datei herunterladen", csv, "alt-texte.csv", "text/csv")
