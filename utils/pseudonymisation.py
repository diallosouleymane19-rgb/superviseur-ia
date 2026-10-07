# -*- coding: utf-8 -*-
"""
Masquage des identifiants avant envoi à l'IA (Mistral) - SMD Global Consulting LLC

Les identifiants sont remplacés par des repères ([EMAIL_1], [SIREN_1]...) avant l'envoi,
puis remis en clair dans la réponse, sur le serveur de l'application.
C'est une pseudonymisation partielle : un nom de personne écrit librement n'est pas détecté.
"""
import re

# Ordre important : les motifs les plus longs d'abord (IBAN avant SIRET, TVA avant SIREN)
_MOTIFS = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?\b")),
    ("TVA", re.compile(r"\bFR[ ]?[0-9A-Z]{2}[ ]?\d{3}[ ]?\d{3}[ ]?\d{3}\b")),
    # SIRET / SIREN uniquement après leur libellé : un montant à 9 chiffres n'est jamais masqué
    ("SIRET", re.compile(r"(?i)(?<=siret)[\s:°n.]{0,6}(\d{3}[ ]?\d{3}[ ]?\d{3}[ ]?\d{5})\b")),
    ("SIREN", re.compile(r"(?i)(?<=siren)[\s:°n.]{0,6}(\d{3}[ ]?\d{3}[ ]?\d{3})\b")),
    ("SIREN", re.compile(r"(?i)(?<=rcs)[\sA-Za-zÀ-ÿ:]{0,30}?(\d{3}[ ]?\d{3}[ ]?\d{3})\b")),
    ("TEL", re.compile(r"(?<![\d,.])(?:\+33[ .]?|0)[1-9](?:[ .]?\d{2}){4}(?![\d,])")),
]


def masquer(texte: str, noms=()):
    """Retourne (texte masqué, table {repère: valeur d'origine})."""
    table, inverse, compteur = {}, {}, {}

    def repere(categorie, valeur):
        if valeur in inverse:
            return inverse[valeur]
        compteur[categorie] = compteur.get(categorie, 0) + 1
        r = f"[{categorie}_{compteur[categorie]}]"
        table[r], inverse[valeur] = valeur, r
        return r

    t = str(texte)
    for nom in sorted({n.strip() for n in noms if n and len(n.strip()) >= 3}, key=len, reverse=True):
        t = re.sub(re.escape(nom), lambda m: repere("ENTREPRISE", m.group(0)), t, flags=re.I)
    for categorie, motif in _MOTIFS:
        def remplacer(m, categorie=categorie):
            if m.groups():   # seul le numéro (groupe 1) est masqué, pas le libellé qui précède
                debut, fin = m.span(1)
                return m.group(0)[:debut - m.start()] + repere(categorie, m.group(1)) + m.group(0)[fin - m.start():]
            return repere(categorie, m.group(0))
        t = motif.sub(remplacer, t)
    return t, table


def demasquer(texte: str, table: dict) -> str:
    """Remet les valeurs d'origine à la place des repères dans la réponse de l'IA."""
    t = str(texte)
    for r, valeur in table.items():
        t = t.replace(r, valeur)
    return t
