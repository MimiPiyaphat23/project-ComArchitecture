import streamlit as st
import pandas as pd

def display_timeline(timeline):
    df = pd.DataFrame(timeline)
    st.subheader("📊 Pipeline Timeline")
    st.dataframe(df)