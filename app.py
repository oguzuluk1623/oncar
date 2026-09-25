import os
import sqlite3
import pandas as pd
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Plaka ve Sigorta Takip Sistemi",
    page_icon="🔐",
    layout="centered",
)

# --- GÜVENLİ GİRİŞ KONTROLÜ ---
# Şifreler artık güvenli alandan (Secrets) okunuyor
try:
    DOGRU_KULLANICI = st.secrets["giris"]["kullanici"]
    DOGRU_SIFRE = st.secrets["giris"]["sifre"]
except Exception:
    # Eğer henüz gizli ayar yapılmadıysa geçici olarak varsayılan kullanır (bilgisayarda test için)
    DOGRU_KULLANICI = "admin"
    DOGRU_SIFRE = "1234"

if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False


def giris_ekrani():
    st.title("🔐 Araç Sigorta Takip - Giriş Ekranı")
    st.write("Lütfen devam etmek için kullanıcı adı ve şifrenizi girin.")

    with st.form("giris_formu"):
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        giris_butonu = st.form_submit_button("Giriş Yap", use_container_width=True)

        if giris_butonu:
            if (
                kullanici_adi == DOGRU_KULLANICI
                and sifre == DOGRU_SIFRE
            ):
                st.session_state.giris_yapildi = True
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")


if not st.session_state.giris_yapildi:
    giris_ekrani()
    st.stop()

# --- ANA PROGRAM ---
with st.sidebar:
    st.write(f"Hoş geldiniz, **{DOGRU_KULLANICI}**")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.giris_yapildi = False
        st.rerun()

KAYIT_KLASORU = "sigorta_dosyalari"
if not os.path.exists(KAYIT_KLASORU):
    os.makedirs(KAYIT_KLASORU)


def veritabani_baglantisi():
    conn = sqlite3.connect("sigorta_takip.db")
    return conn


def tablo_olustur():
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sigortalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plaka TEXT NOT NULL,
            dosya_adi TEXT NOT NULL,
            dosya_yolu TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


tablo_olustur()

st.title("🚗 Araç Sigorta Takip Programı")
st.write(
    "Plaka girişi yapabilir ve ilgili sigorta poliçesini (PDF) kalıcı olarak yönetebilirsiniz."
)

with st.form("sigorta_formu", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        plaka = st.text_input(
            "Araç Plakası", placeholder="Örn: 34ABC123"
        ).upper()

    with col2:
        pdf_dosya = st.file_uploader(
            "Sigorta Poliçesi (PDF)", type=["pdf"]
        )

    submit_button = st.form_submit_button(
        label="Kaydı Ekle", use_container_width=True
    )

    if submit_button:
        if plaka and pdf_dosya:
            dosya_yolu = os.path.join(KAYIT_KLASORU, pdf_dosya.name)

            base, ext = os.path.splitext(pdf_dosya.name)
            sayac = 1
            while os.path.exists(dosya_yolu):
                dosya_yolu = os.path.join(
                    KAYIT_KLASORU, f"{base}_{sayac}{ext}"
                )
                sayac += 1

            with open(dosya_yolu, "wb") as f:
                f.write(pdf_dosya.getbuffer())

            conn = veritabani_baglantisi()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sigortalar (plaka, dosya_adi, dosya_yolu) VALUES (?, ?, ?)",
                (plaka, os.path.basename(dosya_yolu), dosya_yolu),
            )
            conn.commit()
            conn.close()

            st.success(f"'{plaka}' plakalı araç ve sigortası başarıyla eklendi!")
            st.rerun()
        else:
            st.warning("Lütfen hem plaka girin hem de bir PDF dosyası seçin.")

st.markdown("---")
st.subheader("📋 Kayıtlı Araçlar ve Sigortalar")

conn = veritabani_baglantisi()
kayitlar = pd.read_sql_query(
    "SELECT id, plaka, dosya_adi, dosya_yolu FROM sigortalar", conn
)
conn.close()

if not kayitlar.empty:
    for index, row in kayitlar.iterrows():
        col_a, col_b, col_c = st.columns([2, 3, 2])

        with col_a:
            st.markdown(f"**Plaka:** {row['plaka']}")

        with col_b:
            st.markdown(f"**Dosya:** {row['dosya_adi']}")

        with col_c:
            if os.path.exists(row["dosya_yolu"]):
                with open(row["dosya_yolu"], "rb") as f:
                    pdf_verisi = f.read()

                st.download_button(
                    label="📥 PDF İndir",
                    data=pdf_verisi,
                    file_name=row["dosya_adi"],
                    mime="application/pdf",
                    key=f"indir_{row['id']}",
                )
            else:
                st.error("Dosya bulunamadı!")

        st.write("---")
else:
    st.info("Henüz eklenmiş bir kayıt bulunmuyor.")