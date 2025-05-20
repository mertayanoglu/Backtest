import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'strategies'))

import streamlit as st
import pandas as pd
from backtest_demo import (
    BIST_40,
    strateji_ml_temel,
    strateji_rsi_only,
    backtest_strateji
)


st.set_page_config(page_title="Toplu Strateji Backtest", layout="wide")
st.title("📊 Tüm Stratejiler - Tüm Hisseler Backtest Paneli")
st.caption("BIST 40 hisseleri üzerinde tüm stratejiler test edilerek başarı oranı ve portföy performansı hesaplanır.")

strategiler = {
    "ML_Temel": strateji_ml_temel,
    "RSI_Only": strateji_rsi_only,
}

gun_sayisi = st.slider("📅 Geriye dönük gün sayısı", 30, 100, 60)

if st.button("🚀 Tüm Stratejileri Test Et"):
    sonuc = []

    with st.spinner("Testler yapılıyor... Bu işlem birkaç dakika sürebilir."):
        for hisse in BIST_40:
            for ad, fn in strategiler.items():
                try:
                    df_result = backtest_strateji(hisse, fn, gun_sayisi)
                    if not df_result.empty:
                        final_bakiye = df_result["bakiye"].iloc[-1]
                        baslangic = 100000
                        kazanc_yuzde = round((final_bakiye - baslangic) / baslangic * 100, 2)
                        basari = df_result["hedefe_ulaştı"].sum()
                        toplam = len(df_result)
                        oran = round(basari / toplam * 100, 2)

                        sonuc.append({
                            "Hisse": hisse,
                            "Strateji": ad,
                            "Tahmin Sayısı": toplam,
                            "Başarı Oranı (%)": oran,
                            "Son Bakiye (TL)": round(final_bakiye, 2),
                            "Kar/Zarar (%)": kazanc_yuzde
                        })
                except Exception as e:
                    st.warning(f"{hisse}-{ad} hata: {e}")
                    continue

if df_sonuc:
    df_sonuc = pd.DataFrame(df_sonuc)
    st.success("✅ Tüm testler tamamlandı.")
    st.dataframe(df_sonuc.sort_values(by="Kar/Zarar (%)", ascending=False), use_container_width=True)
else:
    st.warning("Hiçbir tahmin verisi alınamadı. Lütfen daha kısa bir gün aralığıyla tekrar deneyin.")

