# -*- coding: utf-8 -*-
"""
utils/theme.py - SMD Global Consulting LLC
Charte visuelle "finance pro clair" injectée dans Streamlit.

Couleurs :
    Marine  #1F4E79  marque, boutons, liens
    Encre   #14273D  titres, texte principal
    Ardoise #52606D  texte secondaire
    Brume   #F2F5F9  menu latéral, fonds secondaires
    Filet   #D8E0EA  traits et bordures
    Vert    #1D6B47  statut conforme
Typo : IBM Plex Sans (chiffres tabulaires).
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --smd-marine: #1F4E79;
  --smd-encre: #14273D;
  --smd-ardoise: #52606D;
  --smd-brume: #F2F5F9;
  --smd-filet: #D8E0EA;
  --smd-vert: #1D6B47;
}

html, body, [class*="st-"], .stMarkdown, h1, h2, h3, h4, h5, h6, button, input, textarea, select, label, p, li {
  font-family: 'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
/* Ne jamais remplacer la police des icônes Streamlit */
[data-testid="stIconMaterial"], .material-symbols-rounded {
  font-family: 'Material Symbols Rounded' !important;
}
h1, h2, h3, h4 { color: var(--smd-encre); letter-spacing: -0.01em; font-weight: 600; }

/* Menu latéral */
[data-testid="stSidebar"] { border-right: 1px solid var(--smd-filet); }
[data-testid="stSidebar"] h1 { font-size: 1.15rem; line-height: 1.3; }

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

/* Ligne de compteurs façon grand livre */
.smd-ligne { display: grid; grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--smd-filet); border-bottom: 1px solid var(--smd-filet);
  margin-bottom: 2rem; }
.smd-ligne > div { padding: .9rem 1rem; border-left: 1px solid var(--smd-filet); }
.smd-ligne > div:first-child { border-left: none; padding-left: 0; }
.smd-ligne .lib { color: var(--smd-ardoise); font-size: .85rem; }
.smd-ligne .val { font-size: 1.5rem; font-weight: 600; color: var(--smd-encre);
  font-variant-numeric: tabular-nums; }

/* Listes de modules et statut */
.smd-modules h4 { font-size: 1rem; margin: 0 0 .4rem; }
.smd-modules ul { list-style: none; margin: 0 !important; padding: 0 !important; color: var(--smd-ardoise); }
.smd-modules li { padding: .1rem 0 !important; margin: 0 !important; font-size: .95rem; }
.smd-statut { display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; color: var(--smd-ardoise);
  font-size: .9rem; border-top: 1px solid var(--smd-filet); padding-top: 1rem; margin-top: 1rem; }
.smd-pastille { display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
  margin-right: .4rem; vertical-align: middle; }
.ok { background: var(--smd-vert); } .ko { background: #B7791F; }

/* Connexion */
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
