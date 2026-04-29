import streamlit as st
import bcrypt

# Identifiants sécurisés
UTILISATEURS = {
    "smdconsulting": bcrypt.hashpw("compta2026".encode(), bcrypt.gensalt()).decode()
}

def verifier_mot_de_passe(username, password):
    if username in UTILISATEURS:
        return bcrypt.checkpw(password.encode(), UTILISATEURS[username].encode())
    return False

def login():
    """
    Page de connexion.
    """
    st.title("🔐 Superviseur IA Comptable")
    st.markdown("### Connexion")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")

        if submit:
            if verifier_mot_de_passe(username, password):
                st.session_state["connecte"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("❌ Identifiant ou mot de passe incorrect.")

def logout():
    """
    Bouton de déconnexion.
    """
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["connecte"] = False
        st.session_state["username"] = ""
        st.rerun()

def is_connecte():
    return st.session_state.get("connecte", False)