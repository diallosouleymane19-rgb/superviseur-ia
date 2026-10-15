# -*- coding: utf-8 -*-
"""
utils/theme.py - SMD Global Consulting LLC
Charte visuelle SMD Global Consulting, complément de .streamlit/config.toml.

Couleurs (relevées sur le logo) :
    Marine  #0A3681  menu latéral, marque, boutons
    Azur    #0A84C6  repère de la page active, accents
    Encre   #0E1E3A  titres, texte principal
    Ardoise #4F5D73  texte secondaire
    Brume   #F3F6FA  fonds secondaires
    Filet   #D9E1EC  traits et bordures
    Vert    #1D6B47  statut conforme
Typo : Source Serif (titres, fournie par Streamlit), IBM Plex Sans (texte, chiffres tabulaires, static/fonts).
"""
import streamlit as st

_CSS = """
<style>

:root {
  --smd-marine: #0A3681;
  --smd-azur: #0A84C6;
  --smd-encre: #0E1E3A;
  --smd-ardoise: #4F5D73;
  --smd-brume: #F3F6FA;
  --smd-filet: #D9E1EC;
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

/* ── Menu latéral aux couleurs SMD ───────────────────────────────────────── */
[data-testid="stSidebarHeader"] { padding-top: 1.25rem; padding-bottom: .5rem; }
[data-testid="stSidebarHeader"] { height: auto !important; }
[data-testid="stSidebarHeader"] img { height: 2.4rem !important; width: auto !important; max-width: 100%; opacity: .9; }
.smd-demo { background: #F2B544; color: #2B1D00; border-radius: 6px; padding: .55rem .75rem;
  font-size: .9rem; font-weight: 500; margin: .25rem 0 .75rem; }
/* Nom du produit : plus visible que la signature SMD */
.smd-produit-menu { font-family: 'Source Serif', Georgia, serif; font-size: 2rem; font-weight: 700; color: #fff;
  line-height: 1.1; margin: .1rem 0 1rem; padding-bottom: .9rem; letter-spacing: -.01em;
  border-bottom: 1px solid rgba(255,255,255,.15); }
.smd-produit-menu span, .smd-produit span { color: #5FB8E6; }
.smd-produit-menu small { display: block; font-family: 'IBM Plex Sans', sans-serif; font-size: .8rem;
  font-weight: 400; color: #B9C8E3; letter-spacing: .02em; margin-top: .2rem; }
.smd-produit { font-family: 'Source Serif', Georgia, serif; font-size: 1.3rem; font-weight: 700;
  color: var(--smd-marine); margin-right: .5rem; }
.smd-produit span { color: var(--smd-azur); }
[data-testid="stSidebar"] hr { border-color: rgba(233,238,247,.18); margin: .9rem 0; }
.smd-utilisateur { font-size: .82rem; color: #B9C6DE; margin: 0 0 .5rem; word-break: break-all; }
.smd-role { border-left: 3px solid var(--smd-azur); padding: .15rem 0 .15rem .65rem; margin: 0 0 .5rem; }
.smd-role-lib { font-weight: 600; color: #FFFFFF; font-size: .9rem; }
.smd-role-plan { display: flex; align-items: center; gap: .45rem; margin-top: .15rem; }
.smd-plan { background: rgba(10,132,198,.35); color: #fff; font-size: .72rem; font-weight: 500;
  padding: .05rem .5rem; border-radius: 999px; }
.smd-role-nom { color: #B9C6DE; font-size: .78rem; }
.smd-quota { font-size: .78rem; color: #B9C6DE; margin: .1rem 0 .25rem; }
.smd-quota b { color: #fff; font-weight: 600; }
.smd-jauge { background: rgba(255,255,255,.15); border-radius: 3px; height: 4px; margin-bottom: .4rem; }
.smd-jauge > div { height: 4px; border-radius: 3px; }
.smd-jauge-ok { background: #3FB37F; } .smd-jauge-moyen { background: #E0A43A; } .smd-jauge-haut { background: #E5534B; }

/* Menu : familles et entrées */
.st-key-smd_menu [data-testid="stMarkdownContainer"] p { margin: 0; }
.st-key-smd_menu .stMarkdown > div { margin-bottom: 0 !important; }
.st-key-smd_menu .stElementContainer:has(.smd-section) { height: auto !important; }
.smd-section { font-size: .76rem; font-weight: 600; color: #8FA6CC; letter-spacing: .02em;
  padding: 1.1rem 0 .35rem .6rem; }
.st-key-smd_menu { gap: 0 !important; }
.st-key-smd_menu .stButton > button { justify-content: flex-start; text-align: left; min-height: 2.1rem;
  padding: .3rem .6rem; border-radius: 4px; border: none; font-size: .9rem; font-weight: 400;
  color: #DCE4F2; background: transparent; }
.st-key-smd_menu .stButton > button:hover { background: rgba(255,255,255,.08); color: #fff; }
.st-key-smd_menu .stButton > button[kind="primary"] { background: rgba(255,255,255,.12); color: #fff;
  font-weight: 600; box-shadow: inset 3px 0 0 var(--smd-azur); }
.st-key-smd_menu .stButton > button p { font-size: .9rem; }
.st-key-smd_menu .stButton > button [data-testid="stIconMaterial"] { color: #8FB8E6; font-size: 1.1rem; }
.st-key-smd_menu .stButton > button[kind="primary"] [data-testid="stIconMaterial"] { color: #fff; }
[data-testid="stSidebar"] .stButton > button[kind="secondary"] { background: transparent; color: #E9EEF7;
  border: 1px solid rgba(233,238,247,.35); }
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover { border-color: #fff; color: #fff; }

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
.smd-tuile .smd-ico { font-size: 1.5rem; color: var(--smd-azur); background: #E6F3FB;
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
  border-color: var(--smd-marine); transform: translateY(-2px); box-shadow: 0 6px 14px rgba(10,54,129,.18); }
.st-key-smd_rapide .stButton > button:hover [data-testid="stIconMaterial"] { color: #fff; }

/* Familles de modules : cartes avec en-tête marine */
[class*="st-key-smd_famille_"] { background: #fff; border: 1px solid var(--smd-filet); border-radius: 8px;
  overflow: hidden; gap: 0 !important; padding-bottom: .5rem; height: 100%; }
.smd-famille { display: flex; align-items: center; gap: .6rem; background: var(--smd-marine); color: #fff;
  padding: .8rem 1rem; font-family: 'Source Serif', Georgia, serif; font-size: 1.05rem; font-weight: 600;
  margin-bottom: .6rem; }
.smd-famille .smd-ico { color: #7CC4EA; font-size: 1.3rem; }
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
.st-key-smd_panneau .smd-accroche { color: #C9D6EC; }
.st-key-smd_panneau .smd-slogan { font-family: 'Source Serif', Georgia, serif; font-size: 1.3rem;
  font-style: italic; color: #FFFFFF; margin: 0 0 1rem; }
/* Pas d'icône de lien à côté des titres */
[data-testid="stHeaderActionElements"], .stMarkdown h1 a[href^="#"], .stMarkdown h2 a[href^="#"],
.stMarkdown h3 a[href^="#"] { display: none !important; }
.st-key-smd_panneau .smd-engagements li { color: #FFFFFF; border-top-color: rgba(233,238,247,.2); }
.st-key-smd_panneau .smd-engagements li::before { border-color: #5FB3E6; }
.st-key-smd_panneau .smd-engagements span { color: #B9C6DE; }
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
