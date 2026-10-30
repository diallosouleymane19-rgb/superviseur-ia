# -*- coding: utf-8 -*-
"""utils/page_vitrine.py - Page publique de présentation de KontrolIA (avant connexion).

Structure inspirée des pages d'accueil SaaS (titre-promesse, coches, appel à l'action unique,
levée des freins, piliers, modules, tarifs, FAQ). Tous les textes décrivent ce que l'appli fait
réellement : aucun avis, aucune note ni aucun label n'est affiché tant qu'il n'existe pas.
"""
import streamlit as st

from utils.stripe_billing import PRICING, FONDATEUR

CONTACT = "contact@smdconsulting.pro"

COCHES = [
    "Balance et FEC contrôlés selon le PCG et les exigences de la DGFiP",
    "Factures lues par OCR et proposées en écritures comptables",
    "Bilan, compte de résultat, SIG, TFT et rapport client prêts à présenter",
    "Vos fichiers sont lus en mémoire, jamais enregistrés",
]

PILIERS = [
    ("bolt", "Rapide", "Déposez une balance ou un FEC : le contrôle est fait en quelques minutes."),
    ("verified", "Conforme PCG et DGFiP",
     "Les contrôles suivent le Plan comptable général et les exigences du FEC (art. A47 A-1 du LPF)."),
    ("shield_lock", "Données protégées",
     "Hébergement en France (OVH). Sauvegardes à votre demande seulement, supprimées après 30 jours."),
]

MODULES = [
    ("fact_check", "Analyse et contrôle",
     ["Factures (OCR) et écritures", "Contrôle de balance", "Loi de Benford", "Alertes et anomalies",
      "Cohérence des données"]),
    ("account_balance", "États financiers",
     ["Bilan", "Compte de résultat et SIG", "Tableau des flux de trésorerie", "Plan de financement",
      "Comparatif N / N-1"]),
    ("inventory_2", "Gestion et clôture",
     ["Immobilisations", "Inventaire et clôture", "Rapprochement bancaire"]),
    ("summarize", "Reporting et fiscal",
     ["Traitement FEC DGFiP", "Aide TVA CA3 / CA12", "Rapport client", "Veille fiscale"]),
]

POUR_QUI = [
    ("groups", "Cabinets et experts-comptables",
     "Contrôlez les dossiers de vos clients avant la révision, à plusieurs dans un même cabinet."),
    ("person", "Comptables indépendants",
     "Sécurisez chaque dossier et présentez des états propres à vos clients."),
    ("apartment", "PME, ETI, DAF et RAF",
     "Vérifiez votre comptabilité interne avant la clôture ou l'échange avec votre expert-comptable."),
]

FAQ = [
    ("Qu'est-ce que KontrolIA ?",
     "Un assistant de contrôle comptable en ligne. Vous déposez une balance, un FEC ou une facture : "
     "KontrolIA vérifie, signale les anomalies et prépare les états financiers selon le PCG. "
     "Vous gardez la décision : « Vous décidez, votre assistant KontrolIA vérifie »."),
    ("L'essai est-il vraiment gratuit ?",
     "Oui. L'essai « Dossier Propre en 14 jours » donne accès au plan Pro complet (tous les modules, "
     "200 analyses) pendant 14 jours, sans carte bancaire. À la fin, votre compte passe au plan Gratuit "
     "(10 analyses par mois), sauf si vous choisissez un abonnement."),
    ("Mes fichiers sont-ils conservés ?",
     "Non. Les fichiers déposés sont lus en mémoire le temps de l'analyse et ne sont pas enregistrés. "
     "Seules les analyses que vous choisissez de sauvegarder sont conservées, en France (OVH), "
     "30 jours au plus."),
    ("Utilisez-vous l'IA sur mes données ?",
     "Certains textes (commentaires, synthèses) sont rédigés par l'IA de Mistral AI et sont toujours "
     "signalés comme tels. Vos données ne servent pas à entraîner l'IA : l'option est désactivée chez "
     "Mistral depuis le 07/10/2026."),
    ("KontrolIA remplace-t-il mon expert-comptable ?",
     "Non. KontrolIA est un outil d'aide au contrôle. Les résultats doivent être vérifiés par un "
     "professionnel, qui reste responsable des décisions prises."),
    ("Puis-je résilier à tout moment ?",
     "Oui, sans engagement. La résiliation se fait depuis le portail Stripe et prend effet à la fin de la "
     "période en cours."),
    ("Comment la TVA est-elle facturée ?",
     "Les prix sont hors taxes. Le service est fourni à des professionnels par une société établie hors "
     "de l'Union européenne : la TVA éventuellement due est autoliquidée par le client. Le paiement est "
     "traité par Stripe."),
]

CSS = """
<style>
.st-key-vitrine_entete { display:flex; align-items:center; }
.vt-marque { font-size:1.9rem; font-weight:800; color:#1F2933; margin:0; line-height:1.1; }
.st-key-vt_essai_hero button, .st-key-vt_essai_final button, .st-key-vt_essai_pro button {
  background:#A9592A !important; border-color:#A9592A !important; color:#FFFFFF !important; font-weight:700 !important; }
.st-key-vt_essai_hero button:hover, .st-key-vt_essai_final button:hover, .st-key-vt_essai_pro button:hover {
  background:#8F4A22 !important; border-color:#8F4A22 !important; }
.vt-marque span { color:#A9592A; } .vt-titre span { color:#E09A62; }
.vt-signature { font-size:.8rem; color:var(--smd-ardoise); margin:.1rem 0 0; }
.st-key-vitrine_hero { background:linear-gradient(135deg,#2D3A47 0%,#1F2933 100%); border-radius:14px;
  padding:3rem 3rem 2.5rem; }
.vt-badge { display:inline-block; background:rgba(224,154,98,.15); color:#F3C9A6; border:1px solid #E09A62;
  border-radius:999px; padding:.25rem .8rem; font-size:.8rem; font-weight:600; letter-spacing:.03em; }
.vt-titre { color:#FFFFFF !important; font-size:2.9rem !important; line-height:1.08 !important;
  font-weight:800 !important; text-transform:uppercase; margin:1rem 0 1.4rem !important; }
.vt-coches { list-style:none; padding:0; margin:0 0 1.6rem; }
.vt-coches li { color:#E6ECF6; font-size:1.05rem; margin:.55rem 0; display:flex; gap:.6rem; align-items:flex-start; }
.vt-coches li:before { content:"✓"; flex-shrink:0; width:1.35rem; height:1.35rem; border-radius:50%;
  background:#E09A62; color:#1F2933; font-weight:800; font-size:.8rem; display:flex;
  align-items:center; justify-content:center; margin-top:.15rem; }
.vt-freins { color:#B8C2CC; font-size:.85rem; margin:.6rem 0 0; }
.vt-carte-hero { background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.18); border-radius:12px;
  padding:1.5rem; color:#E6ECF6; }
.vt-carte-hero h4 { color:#FFFFFF !important; margin:0 0 .8rem !important; }
.vt-carte-hero .vt-ligne { display:flex; justify-content:space-between; border-bottom:1px dashed rgba(255,255,255,.2);
  padding:.45rem 0; font-size:.9rem; }
.vt-ok { color:#7EE2A8; font-weight:700; } .vt-ko { color:#F6B26B; font-weight:700; }
.vt-section { text-align:center; margin:3.2rem 0 1.4rem; }
.vt-section h2 { color:#1F2933 !important; font-weight:800 !important; margin:0 !important; }
.vt-section p { color:var(--smd-ardoise); margin:.4rem 0 0; }
.vt-carte { background:#FFFFFF; border:1px solid var(--smd-filet); border-radius:12px; padding:1.4rem; height:100%; }
.vt-carte h4 { color:#1F2933 !important; margin:.5rem 0 .4rem !important; font-size:1.05rem !important; }
.vt-carte p, .vt-carte li { color:var(--smd-ardoise); font-size:.9rem; margin:0; }
.vt-carte ul { padding-left:1.1rem; margin:0; } .vt-carte li { margin:.25rem 0; }
.vt-ico { font-family:'Material Symbols Rounded'; font-size:1.9rem; color:#A9592A; line-height:1; }
.vt-prix { border:1px solid var(--smd-filet); border-radius:12px; padding:1.4rem 1.2rem; background:#FFFFFF;
  text-align:center; min-height:15.5rem; }
.vt-prix.vt-reco { border:2px solid #A9592A; box-shadow:0 6px 18px rgba(169,89,42,.15); }
.vt-prix .vt-etiquette { display:inline-block; background:#A9592A; color:#FFFFFF; border-radius:999px;
  font-size:.72rem; font-weight:700; padding:.15rem .7rem; margin-bottom:.5rem; }
.vt-prix h4 { color:#1F2933 !important; margin:.2rem 0 !important; }
.vt-prix .vt-montant { font-size:2rem; font-weight:800; color:#1F2933; margin:.4rem 0 0; }
.vt-prix .vt-unite { font-size:.8rem; color:var(--smd-ardoise); }
.vt-prix .vt-detail { font-size:.88rem; color:var(--smd-ardoise); margin:.8rem 0 0; }
.vt-fondateur { background:#FBF3EC; border:1px solid #E09A62; border-radius:12px; padding:1.1rem 1.4rem;
  margin:1.2rem 0 0; color:#2B1A10; }
.vt-fondateur b { color:#8F4A22; }
.st-key-vitrine_final a { color:#A9592A !important; }
.st-key-vitrine_final { background:#F6F1EC; border-radius:14px; padding:2.2rem; text-align:center; }
/* En-tête façon bandeau sombre */
.block-container { padding-top:1.2rem !important; }
.vt-nav { background:#1F2933; border-radius:12px; overflow:hidden; margin:0 0 1.2rem; }
.vt-nav a { text-decoration:none !important; }
.vt-nav-haut { display:flex; justify-content:space-between; align-items:center; background:#161E26;
  padding:.45rem 1.4rem; font-size:.85rem; }
.vt-nav-haut a { color:#E6ECF6 !important; margin-right:1.4rem; display:inline-flex; align-items:center; gap:.35rem; }
.vt-nav-outils a { margin:0 0 0 1.6rem; }
.vt-nav-haut a:hover { color:#FFFFFF !important; }
.vt-i { font-family:'Material Symbols Rounded'; font-size:1.15rem; line-height:1; }
.vt-nav-bas { display:flex; align-items:center; gap:2rem; background:#1F2933;
  padding:.8rem 1.4rem; }
.vt-logo { font-size:1.75rem; font-weight:800; color:#FFFFFF !important; letter-spacing:-.01em; }
.vt-logo span { color:#E09A62; }
.vt-menu { display:flex; gap:.4rem; flex:1; }
.vt-menu a { color:#FFFFFF !important; font-weight:600; padding:.5rem .9rem; border-radius:10px; font-size:.98rem; }
.vt-menu a:hover { background:rgba(255,255,255,.1); }
.vt-cta { background:#A9592A; color:#FFFFFF !important; font-weight:700; padding:.65rem 1.4rem; border-radius:999px;
  white-space:nowrap; }
.vt-cta:hover { background:#8F4A22; }
@media (max-width: 760px) {
  .vt-nav-public, .vt-menu, .vt-nav-outils a:first-child { display:none; }
  .vt-nav-haut { justify-content:flex-end; }
  .vt-nav-bas { justify-content:space-between; gap:.8rem; padding:.7rem 1rem; }
  .vt-logo { font-size:1.4rem; } .vt-cta { padding:.5rem .9rem; font-size:.85rem; }
  .st-key-vitrine_hero { padding:1.6rem 1.2rem; }
  .vt-titre { font-size:1.9rem !important; }
}
</style>
"""


def _ouvrir(inscription: bool, plan: str | None = None):
    """Quitte la vitrine vers l'écran d'inscription (inscription=True) ou de connexion."""
    st.session_state["vitrine_vue"] = True
    st.session_state["ouvrir_inscription"] = inscription
    if plan:
        st.session_state["plan_vitrine"] = plan
    else:
        st.session_state.pop("plan_vitrine", None)


def _bouton_essai(cle: str, libelle: str = "Essayer gratuitement 14 jours"):
    st.button(libelle, type="primary", key=cle, on_click=_ouvrir, args=(True,), icon=":material/rocket_launch:")


def _euros(centimes: int) -> str:
    e = centimes / 100
    txt = f"{e:,.2f}".replace(",", " ").replace(".", ",")
    return txt[:-3] if txt.endswith(",00") else txt


def _places_fondateur() -> int:
    try:
        from utils.page_inscription import _places_fondateur as places
        from utils.stripe_billing import paiement_actif
        return places() if paiement_actif() else 0
    except Exception:
        return 0


def page_vitrine():
    st.markdown(CSS, unsafe_allow_html=True)

    # ── En-tête (deux bandeaux, liens internes ; connexion / inscription via ?acces=…) ──
    st.markdown(
        "<div class='vt-nav'>"
        "<div class='vt-nav-haut'><div class='vt-nav-public'>"
        "<a href='#pour-qui' target='_self'>Cabinets</a><a href='#pour-qui' target='_self'>Entreprises</a></div>"
        "<div class='vt-nav-outils'>"
        f"<a href='mailto:{CONTACT}'><span class='vt-i'>mail</span>{CONTACT}</a>"
        "<a href='#faq' target='_self'><span class='vt-i'>help</span>Aide</a>"
        "<a href='?acces=connexion' target='_self'><span class='vt-i'>account_circle</span>Me connecter</a>"
        "</div></div>"
        "<div class='vt-nav-bas'>"
        "<a class='vt-logo' href='#haut' target='_self'>Kontrol<span>IA</span></a>"
        "<nav class='vt-menu'>"
        "<a href='#fonctionnalites' target='_self'>Fonctionnalités</a>"
        "<a href='#pour-qui' target='_self'>Pour qui</a>"
        "<a href='#tarifs' target='_self'>Tarifs</a>"
        "<a href='#faq' target='_self'>FAQ</a></nav>"
        "<a class='vt-cta' href='?acces=inscription' target='_self'>S'inscrire gratuitement</a>"
        "</div></div><div id='haut'></div>", unsafe_allow_html=True)

    # ── Bandeau d'accueil ──────────────────────────────────────────────────────
    with st.container(key="vitrine_hero"):
        g, _, d = st.columns([6, .4, 4])
        with g:
            coches = "".join(f"<li>{c}</li>" for c in COCHES)
            st.markdown(
                "<span class='vt-badge'>Dossier Propre en 14 jours</span>"
                "<h1 class='vt-titre'>Vos contrôles comptables, vérifiés par Kontrol<span>IA</span></h1>"
                f"<ul class='vt-coches'>{coches}</ul>", unsafe_allow_html=True)
            b1, b2 = st.columns([1.15, 1])
            with b1:
                _bouton_essai("vt_essai_hero")
            with b2:
                st.markdown("<a href='#tarifs' style='display:inline-block;margin-top:.45rem;color:#FFFFFF;"
                            "font-weight:600'>Découvrir nos offres →</a>", unsafe_allow_html=True)
            st.markdown("<p class='vt-freins'>Sans engagement · Aucune carte bancaire pour l'essai · "
                        "Inscription en 1 minute</p>", unsafe_allow_html=True)
        with d:
            st.markdown(
                "<div class='vt-carte-hero'><h4>Exemple de contrôle de balance</h4>"
                "<div class='vt-ligne'><span>Équilibre débit / crédit</span><span class='vt-ok'>Conforme</span></div>"
                "<div class='vt-ligne'><span>Analyse par classe PCG</span><span class='vt-ok'>Conforme</span></div>"
                "<div class='vt-ligne'><span>Charges créditrices (classe 6)</span><span class='vt-ko'>À vérifier</span></div>"
                "<div class='vt-ligne'><span>Produits débiteurs (classe 7)</span><span class='vt-ko'>À vérifier</span></div>"
                "<div class='vt-ligne' style='border:0'><span>Rapport d'audit</span><span class='vt-ok'>Prêt</span></div>"
                "<p style='font-size:.75rem;color:#B8C2CC;margin:.8rem 0 0'>Illustration : les contrôles affichés "
                "dépendent du fichier déposé.</p></div>", unsafe_allow_html=True)

    # ── Trois piliers ──────────────────────────────────────────────────────────
    st.markdown("<div class='vt-section'><h2>Pourquoi choisir KontrolIA ?</h2>"
                "<p>Pensé par un comptable, pour les comptables et les dirigeants.</p></div>", unsafe_allow_html=True)
    for col, (ico, titre, texte) in zip(st.columns(3), PILIERS):
        with col:
            st.markdown(f"<div class='vt-carte'><span class='vt-ico'>{ico}</span><h4>{titre}</h4><p>{texte}</p></div>",
                        unsafe_allow_html=True)

    # ── Modules ────────────────────────────────────────────────────────────────
    st.markdown("<div id='fonctionnalites' class='vt-section'><h2>Une seule appli pour tout le dossier</h2>"
                "<p>Tous les modules sont inclus dans l'essai.</p></div>", unsafe_allow_html=True)
    for col, (ico, titre, items) in zip(st.columns(4), MODULES):
        with col:
            lis = "".join(f"<li>{i}</li>" for i in items)
            st.markdown(f"<div class='vt-carte'><span class='vt-ico'>{ico}</span><h4>{titre}</h4><ul>{lis}</ul></div>",
                        unsafe_allow_html=True)

    # ── Pour qui ───────────────────────────────────────────────────────────────
    st.markdown("<div id='pour-qui' class='vt-section'><h2>Pour qui ?</h2></div>", unsafe_allow_html=True)
    for col, (ico, titre, texte) in zip(st.columns(3), POUR_QUI):
        with col:
            st.markdown(f"<div class='vt-carte'><span class='vt-ico'>{ico}</span><h4>{titre}</h4><p>{texte}</p></div>",
                        unsafe_allow_html=True)

    # ── Tarifs ─────────────────────────────────────────────────────────────────
    st.markdown("<div id='tarifs' class='vt-section'><h2>Des offres simples</h2>"
                "<p>Prix hors taxes · sans engagement · résiliable à tout moment</p></div>", unsafe_allow_html=True)
    offres = [
        ("free", "Gratuit", None, "10 analyses par mois", False),
        ("starter", PRICING["starter"]["label"], PRICING["starter"], "50 analyses par mois", False),
        ("pro", PRICING["pro"]["label"], PRICING["pro"], "200 analyses par mois · tous les modules", True),
        ("enterprise", PRICING["enterprise"]["label"], PRICING["enterprise"], "Analyses illimitées", False),
    ]
    for col, (code, nom, prix, detail, reco) in zip(st.columns(4), offres):
        with col:
            if prix:
                montant = f"{_euros(prix['monthly'])} €"
                unite = f"HT / mois · ou {_euros(prix['annual'])} € HT / an"
            else:
                montant, unite = "0 €", "pour toujours"
            etiquette = ("<span class='vt-etiquette'{}>Essai 14 jours offert</span><br>"
                         .format("" if reco else " style='visibility:hidden'"))
            st.markdown(
                f"<div class='vt-prix{' vt-reco' if reco else ''}'>{etiquette}<h4>{nom}</h4>"
                f"<p class='vt-montant'>{montant}</p><span class='vt-unite'>{unite}</span>"
                f"<p class='vt-detail'>{detail}</p></div>", unsafe_allow_html=True)
            if reco:
                st.button("Essayer 14 jours gratuits", type="primary", key="vt_essai_pro", on_click=_ouvrir,
                          args=(True,), icon=":material/rocket_launch:", width="stretch")
            else:
                st.button("Démarrer gratuitement" if code == "free" else f"Choisir {nom}", key=f"vt_plan_{code}",
                          on_click=_ouvrir, args=(True, None if code == "free" else code), width="stretch")

    places = _places_fondateur()
    if places > 0:
        st.markdown(
            "<div class='vt-fondateur'><b>Programme Cabinet Fondateur</b> — plan Pro complet à "
            f"<b>29,99 € HT/mois</b> les 3 premiers mois, puis <b>49,99 € HT/mois garanti</b> "
            f"tant que l'abonnement reste actif. Réservé aux 25 premiers abonnés : "
            f"<b>{places} place{'s' if places > 1 else ''} restante{'s' if places > 1 else ''}</b>.</div>",
            unsafe_allow_html=True)
        st.button("Devenir Cabinet Fondateur", key="vt_plan_fondateur", on_click=_ouvrir,
                  args=(True, FONDATEUR["plan"]), icon=":material/workspace_premium:")

    # ── FAQ ────────────────────────────────────────────────────────────────────
    st.markdown("<div id='faq' class='vt-section'><h2>Questions fréquentes</h2></div>", unsafe_allow_html=True)
    _, centre, _ = st.columns([1, 6, 1])
    with centre:
        for q, r in FAQ:
            with st.expander(q):
                st.write(r)

    # ── Appel final et contact ─────────────────────────────────────────────────
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    with st.container(key="vitrine_final"):
        st.markdown("<h2 style='margin:0 0 .4rem'>Prêt à contrôler votre premier dossier ?</h2>"
                    f"<p style='color:var(--smd-ardoise)'>Une question ? Écrivez-nous : "
                    f"<a href='mailto:{CONTACT}'>{CONTACT}</a></p>", unsafe_allow_html=True)
        _, c, _ = st.columns([2, 1.4, 2])
        with c:
            _bouton_essai("vt_essai_final")

    st.caption("SMD Global Consulting LLC © 2026 · [CGU](?doc=cgu) · "
               "[Politique de confidentialité](?doc=confidentialite)")
