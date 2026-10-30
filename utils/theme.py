# -*- coding: utf-8 -*-
"""
utils/theme.py - SMD Global Consulting LLC
Charte visuelle SMD Global Consulting, complément de .streamlit/config.toml.

Couleurs (relevées sur le logo) :
    Charte « Graphite & Cuivre » (30/10/2026) ; les noms de variables historiques sont conservés.
    Marine  #1F2933  graphite : bandeaux, boutons principaux
    Azur    #A9592A  cuivre : page active, accents (texte blanc lisible, contraste 5:1)
    Encre   #1F2933  titres, texte principal
    Ardoise #5B6573  texte secondaire
    Brume   #F5F3F0  fonds secondaires
    Filet   #E2E5E9  traits et bordures
    Vert    #1D6B47  statut conforme
Typo : Source Serif (titres, fournie par Streamlit), IBM Plex Sans (texte, chiffres tabulaires, static/fonts).
"""
import streamlit as st

_CSS = """
<style>

:root {
  --smd-marine: #1F2933;
  --smd-azur: #A9592A;
  --smd-encre: #1F2933;
  --smd-ardoise: #5B6573;
  --smd-brume: #F5F3F0;
  --smd-filet: #E2E5E9;
  --smd-vert: #1D6B47;
}

html, body, [class*="st-"], .stMarkdown, button, input, textarea, select, label, p, li {
  font-family: 'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
h1, h2, h3, h4, .smd-entete h1 { font-family: 'Source Serif', Georgia, serif !important; }
[data-testid="stMain"] { font-variant-numeric: tabular-nums; }
/* Ne jamais remplacer la police des icônes Streamlit */
[data-testid="stIconMaterial"], [data-testid$="DynamicIcon"], .material-symbols-rounded {
  font-family: 'Material Symbols Rounded' !important;
}
h1, h2, h3, h4 { color: var(--smd-encre); letter-spacing: -0.005em; font-weight: 600; }

/* ── Menu latéral clair (navigation seulement) ────────────────────────────── */
[data-testid="stSidebar"] { border-right: 1px solid var(--smd-filet); }
[data-testid="stSidebarHeader"] { padding-top: .6rem; padding-bottom: 0; height: auto !important; }
[data-testid="stSidebarUserContent"] { padding-top: 0 !important; }
.smd-demo { background: #FBF0E6; color: #5A2E12; border: 1px solid #E8C3A3; border-radius: 8px;
  padding: .55rem .75rem; font-size: .85rem; margin: .75rem 0 0; }
.smd-produit-menu { font-family: 'IBM Plex Sans', sans-serif; font-size: 1.7rem; font-weight: 700;
  color: var(--smd-encre); line-height: 1.1; margin: 0 0 .9rem .3rem; padding-bottom: .9rem; letter-spacing: -.01em;
  border-bottom: 1px solid var(--smd-filet); }
.smd-produit-menu span, .smd-produit span { color: var(--smd-azur); }
.smd-produit { font-family: 'Source Serif', Georgia, serif; font-size: 1.3rem; font-weight: 700;
  color: var(--smd-marine); margin-right: .5rem; }
[data-testid="stSidebar"] hr { border-color: var(--smd-filet); margin: .9rem 0; }

/* Menu du compte (barre du haut) */
.smd-role { border-left: 3px solid var(--smd-azur); padding: .15rem 0 .15rem .65rem; margin: .2rem 0 .6rem; }
.smd-role-lib { font-weight: 600; color: var(--smd-encre); font-size: .92rem; }
.smd-role-plan { display: flex; align-items: center; gap: .45rem; margin-top: .2rem; }
.smd-plan { background: #F6ECE4; color: #8F4A22; font-size: .74rem; font-weight: 600;
  padding: .05rem .55rem; border-radius: 999px; }
.smd-role-nom { color: var(--smd-ardoise); font-size: .8rem; }
.smd-quota { font-size: .82rem; color: var(--smd-ardoise); margin: .1rem 0 .3rem; }
.smd-quota b { color: var(--smd-encre); font-weight: 600; }
.smd-jauge { background: #ECEEF1; border-radius: 3px; height: 5px; margin-bottom: .6rem; }
.smd-jauge > div { height: 5px; border-radius: 3px; }
.smd-jauge-ok { background: #3FB37F; } .smd-jauge-moyen { background: #E0A43A; } .smd-jauge-haut { background: #E5534B; }
.st-key-smd_barre { border-bottom: 1px solid var(--smd-filet); padding-bottom: .6rem; margin: -2.2rem 0 1.2rem; }
.st-key-smd_barre [data-testid="stPopover"] button { border-radius: 999px; }

/* Familles repliables et entrées */
.st-key-smd_menu { gap: .1rem !important; }
.st-key-smd_menu .stButton > button { justify-content: flex-start; text-align: left; min-height: 2.2rem;
  padding: .35rem .75rem; border-radius: 10px; border: none; font-size: .95rem; font-weight: 400;
  color: var(--smd-encre); background: transparent; }
.st-key-smd_menu .stButton > button p { font-size: .95rem; }
.st-key-smd_menu .stButton > button:hover { background: #F4F5F7; color: var(--smd-encre); }
.st-key-smd_menu [class*="st-key-famille_"] .stButton > button { margin-top: .35rem; }
.st-key-smd_menu [class*="st-key-famille_"] .stButton > button p { font-weight: 600; }
.st-key-smd_menu [class*="st-key-famille_"] .stButton > button [data-testid="stIconMaterial"] { color: #8A93A0; }
.st-key-smd_menu [class*="st-key-menu_"] .stButton > button:not(:has([data-testid="stIconMaterial"])) {
  padding-left: 2.3rem; color: #3D4652; }
.st-key-smd_menu .stButton > button [data-testid="stIconMaterial"] { color: #5B6573; font-size: 1.15rem; }
.st-key-smd_menu .stButton > button[kind="primary"] { background: var(--smd-azur) !important; color: #fff !important;
  font-weight: 600; box-shadow: 0 2px 6px rgba(169,89,42,.25); }
.st-key-smd_menu .stButton > button[kind="primary"] p,
.st-key-smd_menu .stButton > button[kind="primary"] [data-testid="stIconMaterial"] { color: #fff !important; }
.smd-carte-essai { background: #FBF0E6; border: 1px solid #E8C3A3; border-radius: 10px; padding: .7rem .85rem;
  font-size: .85rem; color: #5A2E12; margin: 1rem 0 .4rem; }
.smd-carte-essai span { color: #7A4A2C; font-size: .8rem; }
.st-key-smd_raccourcis { border-top: 1px solid var(--smd-filet); padding-top: .7rem; margin-top: .6rem; gap: .1rem !important; }
.st-key-smd_raccourcis .stButton > button { justify-content: flex-start; font-weight: 600; font-size: .9rem;
  color: var(--smd-encre); padding: .35rem .5rem; min-height: 2.2rem; }
.st-key-smd_raccourcis .stButton > button [data-testid="stIconMaterial"] { color: var(--smd-azur);
  background: #F6ECE4; border-radius: 50%; padding: .3rem; font-size: 1.05rem; }
.st-key-smd_raccourcis .stButton > button:hover { background: #F4F5F7; }
[data-testid="stSidebar"] .stButton > button[kind="secondary"] { background: #fff; color: var(--smd-encre);
  border: 1px solid var(--smd-filet); }

/* Dépôt de fichier : textes en français (Streamlit les affiche en anglais) */
[data-testid="stFileUploaderDropzoneInstructions"] div > span:first-child { font-size: 0; }
[data-testid="stFileUploaderDropzoneInstructions"] div > span:first-child::after {
  content: "Glissez-déposez votre fichier ici"; font-size: 1rem; }
[data-testid="stFileUploaderDropzoneInstructions"] div > span:last-child { font-size: 0; }
[data-testid="stFileUploaderDropzoneInstructions"] div > span:last-child::after {
  content: "200 Mo maximum par fichier"; font-size: .85rem; }
[data-testid="stFileUploaderDropzone"] button { font-size: 0 !important; }
[data-testid="stFileUploaderDropzone"] button::after { content: "Parcourir"; font-size: .95rem; }

/* Boutons secondaires : contour marine discret */
.stButton > button[kind="secondary"] {
  border: 1px solid var(--smd-filet); color: var(--smd-encre); background: #fff;
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--smd-marine); color: var(--smd-marine);
}
.stButton > button:focus-visible, a:focus-visible {
  outline: 2px solid var(--smd-marine); outline-offset: 2px;
}

/* En-tête d'accueil */
.smd-entete { display: flex; justify-content: space-between; align-items: baseline;
  flex-wrap: wrap; gap: .5rem 2rem; margin: .5rem 0 1.25rem; }
.smd-entete h1 { margin: 0; padding: 0; font-size: 2rem; }
.smd-entete p { margin: .25rem 0 0; color: var(--smd-ardoise); }
.smd-date { color: var(--smd-ardoise); font-size: .95rem; }

/* Bandeau échéance : l'élément fort de la page */
.smd-cta { margin: .25rem 0 .5rem; color: var(--smd-marine); font-weight: 500; }
.smd-echeance { background: var(--smd-marine); color: #fff; border-radius: 6px;
  padding: 1.1rem 1.4rem; display: grid; grid-template-columns: auto 1fr auto;
  gap: .25rem 1.75rem; align-items: center; margin-bottom: 1.75rem; }
.smd-echeance .lib { font-size: .85rem; opacity: .8; grid-column: 1 / -1; }
.smd-echeance .date { font-size: 1.6rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.smd-echeance .quoi { font-size: 1.05rem; }
.smd-echeance .delai { font-variant-numeric: tabular-nums; white-space: nowrap;
  border: 1px solid rgba(255,255,255,.45); border-radius: 999px; padding: .2rem .8rem; }

/* Tuiles de compteurs */
.smd-ico { font-family: 'Material Symbols Rounded' !important; font-weight: normal; font-style: normal;
  line-height: 1; letter-spacing: normal; text-transform: none; white-space: nowrap;
  font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased; }
.smd-tuiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.smd-tuile { display: flex; gap: .9rem; align-items: center; background: #fff;
  border: 1px solid var(--smd-filet); border-top: 3px solid var(--smd-azur); border-radius: 8px;
  padding: 1rem 1.1rem; box-shadow: 0 1px 2px rgba(14,30,58,.05); }
.smd-tuile .smd-ico { font-size: 1.5rem; color: var(--smd-azur); background: #F6ECE4;
  border-radius: 50%; padding: .55rem; }
.smd-tuile .lib { color: var(--smd-ardoise); font-size: .85rem; }
.smd-tuile .val { font-size: 1.45rem; font-weight: 600; color: var(--smd-encre); font-variant-numeric: tabular-nums; }
@media (max-width: 900px) { .smd-tuiles { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .smd-tuile .smd-ico { display: none; } .smd-tuile { padding: .8rem .9rem; }
  .smd-tuile .val { font-size: 1.25rem; } }

/* Accès rapide : cartes d'action */
.st-key-smd_rapide .stButton > button {
  min-height: 4.2rem; justify-content: flex-start; padding: .75rem 1.1rem; background: #fff;
  border: 1px solid var(--smd-filet); border-left: 4px solid var(--smd-azur); border-radius: 8px;
  color: var(--smd-encre); font-weight: 500; font-size: 1rem;
  box-shadow: 0 1px 2px rgba(14,30,58,.05); transition: transform .15s, box-shadow .15s, background .15s; }
.st-key-smd_rapide .stButton > button [data-testid="stIconMaterial"] { color: var(--smd-azur); font-size: 1.5rem; }
.st-key-smd_rapide .stButton > button:hover { background: var(--smd-marine); color: #fff;
  border-color: var(--smd-marine); transform: translateY(-2px); box-shadow: 0 6px 14px rgba(31,41,51,.18); }
.st-key-smd_rapide .stButton > button:hover [data-testid="stIconMaterial"] { color: #fff; }

/* Familles de modules : cartes avec en-tête marine */
[class*="st-key-smd_famille_"] { background: #fff; border: 1px solid var(--smd-filet); border-radius: 8px;
  overflow: hidden; gap: 0 !important; padding-bottom: .5rem; height: 100%; }
.smd-famille { display: flex; align-items: center; gap: .6rem; background: var(--smd-marine); color: #fff;
  padding: .8rem 1rem; font-family: 'Source Serif', Georgia, serif; font-size: 1.05rem; font-weight: 600;
  margin-bottom: .6rem; }
.smd-famille .smd-ico { color: #E09A62; font-size: 1.3rem; }
[class*="st-key-smd_famille_"] .stButton > button { justify-content: flex-start; padding: .35rem 1rem;
  color: var(--smd-ardoise); font-size: .95rem; min-height: 0; }
[class*="st-key-smd_famille_"] .stButton > button > span { order: 2; margin-left: auto; }
[class*="st-key-smd_famille_"] .stButton > button > div { order: 1; text-align: left; }
[class*="st-key-smd_famille_"] .stButton > button [data-testid="stIconMaterial"] { color: #B8C4D6;
  transition: color .15s, transform .15s; }
[class*="st-key-smd_famille_"] .stButton > button:hover { color: var(--smd-marine); background: var(--smd-brume); }
[class*="st-key-smd_famille_"] .stButton > button:hover [data-testid="stIconMaterial"] { color: var(--smd-azur);
  transform: translateX(3px); }
[class*="st-key-smd_famille_"] [data-testid="stElementContainer"]:has(.smd-famille) { margin-bottom: .4rem; }
.smd-statut { display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; color: var(--smd-ardoise);
  font-size: .9rem; border-top: 1px solid var(--smd-filet); padding-top: 1rem; margin-top: 1rem; }
.smd-pastille { display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
  margin-right: .4rem; vertical-align: middle; }
.ok { background: var(--smd-vert); } .ko { background: #B7791F; }

/* Connexion : panneau aux couleurs SMD */
.st-key-smd_panneau { background: var(--smd-marine); border-radius: 8px; padding: 2rem 2.25rem 2.25rem; }
.st-key-smd_panneau .smd-logo { height: 4.2rem; width: auto; margin: 0 0 1.75rem -.25rem; display: block; }
.st-key-smd_panneau h1 { color: #FFFFFF !important; }
.st-key-smd_panneau .smd-accroche { color: #C5CCD3; }
.st-key-smd_panneau .smd-slogan { font-family: 'Source Serif', Georgia, serif; font-size: 1.3rem;
  font-style: italic; color: #FFFFFF; margin: 0 0 1rem; }
/* Pas d'icône de lien à côté des titres */
[data-testid="stHeaderActionElements"], .stMarkdown h1 a[href^="#"], .stMarkdown h2 a[href^="#"],
.stMarkdown h3 a[href^="#"] { display: none !important; }
.st-key-smd_panneau .smd-engagements li { color: #FFFFFF; border-top-color: rgba(233,238,247,.2); }
.st-key-smd_panneau .smd-engagements li::before { border-color: #E09A62; }
.st-key-smd_panneau .smd-engagements span { color: #B8C2CC; }
.smd-marque { color: var(--smd-ardoise); font-size: .95rem; margin-bottom: .5rem; }
.smd-accroche { font-size: 1.1rem; color: var(--smd-ardoise); max-width: 34rem; line-height: 1.55; }
.smd-engagements { list-style: none; padding: 0 !important; margin: 1.5rem 0 0 !important; max-width: 34rem; }
.smd-engagements li { margin: 0 !important; padding: .65rem 0 .65rem 1.6rem; border-top: 1px solid var(--smd-filet);
  position: relative; color: var(--smd-encre); }
.smd-engagements li::before { content: ""; position: absolute; left: 0; top: 1rem;
  width: .7rem; height: .4rem; border-left: 2px solid var(--smd-marine);
  border-bottom: 2px solid var(--smd-marine); transform: rotate(-45deg); }
.smd-engagements span { color: var(--smd-ardoise); }

@media (max-width: 640px) {
  .smd-echeance { grid-template-columns: 1fr; }
  .smd-echeance .delai { justify-self: start; }
  .smd-ligne { grid-template-columns: repeat(2, 1fr); }
  .smd-ligne > div:nth-child(3) { border-left: none; padding-left: 0; }
  .smd-ligne > div:nth-child(n+3) { border-top: 1px solid var(--smd-filet); }
  .smd-entete h1 { font-size: 1.6rem; }
}
</style>
"""


def appliquer_theme():
    """Injecte la charte graphique. À appeler une fois, juste après set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)
