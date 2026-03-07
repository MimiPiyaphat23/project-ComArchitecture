import streamlit as st
import pandas as pd

stage_colors = {
    "IF": "background-color:#4FC3F7",
    "ID": "background-color:#81C784",
    "EX": "background-color:#FFD54F",
    "MEM": "background-color:#FFB74D",
    "WB": "background-color:#E57373",
}

def color_stage(val):
    return stage_colors.get(val, "")

def display_timeline(timeline):

    df = pd.DataFrame(timeline)

    styled = df.style.applymap(color_stage)

    st.dataframe(
        styled,
        use_container_width=True
    )