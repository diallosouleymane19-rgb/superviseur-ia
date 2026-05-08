# -*- coding: utf-8 -*-
"""Script de patch - Ajout Confidentialité & Sécurité"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ── MODIFICATION 1 : Menu sidebar ──────────────────────────────────────────
content = content.replace(
    '        "📰 Veille Fiscale"\n    ]',
    '        "📰 Veille Fiscale",\n        "🔒 Confidentialité & Sécurité"\n    ]'
)

# ── MODIFICATION 2 : Page de connexion ─────────────────────────────────────
content = content.replace(
    '        st.markdown("---")\n        email = st.text_input("📧 Email professionnel"',
    '''        st.markdown("---")
        st.markdown("""
        <div style='background:#f0fdf4;padding:12px;border-radius:8px;margin-bottom:10px;font-size:0.85em'>
        ✅ <b>Données anonymisées</b> — SIRET masqués, noms supprimés<br>
        ✅ <b>Non stockées</b> — Aucune conservation après analyse<br>
        ✅ <b>Non utilisées pour entraîner l\'IA</b> — Politique Mistral garantie
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        email = st.text_input("📧 Email professionnel"'''
)

# ── MODIFICATION 3 : Section accueil ───────────────────────────────────────
content = content.replace(
    '    st.divider()\n    st.caption("**SMD Consulting** - Comptable IA Augmenté © 2026")',
    '''    st.divider()
    st.markdown("### 🔒 Vos Données Sont Protégées")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ **Anonymisation**\\n\\nSIRET masqués, noms supprimés avant envoi")
    with col2:
        st.success("✅ **Non stockées**\\n\\nAucune conservation après analyse")
    with col3:
        st.success("✅ **IA éthique**\\n\\nDonnées non utilisées pour entraîner Mistral")
    st.divider()
    st.caption("**SMD Consulting** - Comptable IA Augmenté © 2026")'''
)

# ── MODIFICATION 4 : Nouvelle page Confidentialité ─────────────────────────
new_page = '''
# -----------------------------------------------------------------------------
# 13. CONFIDENTIALITÉ & SÉCURITÉ
# -----------------------------------------------------------------------------

elif page == "🔒 Confidentialité & Sécurité":
    st.title("🔒 Confidentialité & Sécurité")
    st.markdown("**Engagements SMD Consulting** envers la protection de vos données")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("### ✅ Anonymisation\\n\\nVous transmettez uniquement des données anonymisées : SIRET masqués, noms supprimés, données sensibles retirées.")
    with col2:
        st.success("### ✅ Non stockées\\n\\nVos données ne sont pas conservées après analyse. Une convention de test est disponible sur demande.")
    with col3:
        st.success("### ✅ IA éthique\\n\\nVos données ne servent pas à entraîner Mistral AI — garanti contractuellement.")

    st.divider()
    st.markdown("### 📋 Convention de Test")
    st.info("""
**CONVENTION DE TEST - SMD Consulting**

Entre **SMD Consulting** (Souleymane Diallo) et le client soussigné, il est convenu que :

1. Les données transmises sont utilisées **uniquement** pour la démonstration du Superviseur IA Comptable
2. **Aucune donnée n\'est conservée** au-delà de la session d\'analyse
3. Les données ne sont **pas partagées** avec des tiers
4. Les données ne sont **pas utilisées** pour entraîner des modèles d\'IA
5. Le client s\'engage à transmettre des données **préalablement anonymisées**

*Version signée disponible sur demande : smdconsulting@gmail.com*
    """)

    st.divider()
    st.markdown("### 🛡️ Cadre Réglementaire")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**RGPD**
- Traitement limité à la finalité déclarée
- Durée de conservation minimale
- Droit d\'accès et suppression garanti
- Pas de transfert hors UE sans garanties
        """)
    with col2:
        st.markdown("""
**Mistral AI**
- Données API non utilisées pour l\'entraînement
- Hébergement en Europe
- Conformité RGPD certifiée
- Chiffrement HTTPS/TLS
        """)

    st.divider()
    st.markdown("📧 **Contact** : smdconsulting@gmail.com")
    st.caption("SMD Consulting © 2026 - Comptable IA Augmenté")

'''

content = content.replace(
    '# =============================================================================\n# FOOTER',
    new_page + '# =============================================================================\n# FOOTER'
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Patch appliqué avec succès !")
print("   - Menu mis à jour")
print("   - Page connexion mise à jour")
print("   - Accueil mis à jour")
print("   - Page Confidentialité ajoutée")