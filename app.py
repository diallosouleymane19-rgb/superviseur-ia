# -*- coding: utf-8 -*-
"""
Ancienne adresse de l'application (Streamlit Community Cloud).
L'application s'appelle désormais KontrolIA et est hébergée en France (OVH) :
https://app.smdconsulting.pro
Cette page ne fait que rediriger les visiteurs ; aucune donnée n'est lue ni enregistrée ici.
"""
import streamlit as st

NOUVELLE_ADRESSE = "https://app.smdconsulting.pro"

st.set_page_config(page_title="KontrolIA a déménagé", layout="centered")

st.title("KontrolIA a déménagé")
st.markdown(
    "L'application **Superviseur IA Comptable** s'appelle désormais **KontrolIA**. "
    "Elle est hébergée en France (OVH) à l'adresse ci-dessous. "
    "Vos identifiants, vos dossiers clients et vos analyses sauvegardées y ont été transférés."
)
st.link_button("Ouvrir KontrolIA", NOUVELLE_ADRESSE, type="primary", width="stretch")
st.caption(f"Adresse à enregistrer dans vos favoris : {NOUVELLE_ADRESSE}")
st.caption("SMD Global Consulting LLC · contact@smdconsulting.pro")

