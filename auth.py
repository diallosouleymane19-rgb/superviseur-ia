import streamlit as st

def login():
    st.title("🔐 Superviseur IA Comptable")
    st.markdown("### Accès réservé aux cabinets clients")
    
    email = st.text_input("Email professionnel")
    password = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter", type="primary"):
        # Récupération des identifiants depuis les secrets
        try:
            valid_email = st.secrets["USER_EMAIL"]
            valid_password = st.secrets["USER_PASSWORD"]
        except:
            st.error("❌ Configuration manquante. Contactez l'administrateur.")
            return
        
        if email == valid_email and password == valid_password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = email.split("@")[0]
            st.success("✅ Connexion réussie")
            st.rerun()
        else:
            st.error("❌ Email ou mot de passe incorrect")

def is_connecte():
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get("authenticated", False)

def logout():
    """Déconnexion"""
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["authenticated"] = False
        st.rerun()
