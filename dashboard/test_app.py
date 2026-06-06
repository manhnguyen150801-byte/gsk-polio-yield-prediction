import streamlit as st

st.set_page_config(page_title="Streamlit Test", layout="wide")

st.title("Streamlit is working")
st.write("This is a clean test file, separate from app.py.")

st.sidebar.title("Navigation")
st.sidebar.radio("Page", ["Home", "Basetable", "Analysis"])