from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

IPTC_IA = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def marquer_docx_ia(doc, mention, modele="", date_iso=""):
    """Marquage lisible par machine d'un document rédigé par IA (AI Act, art. 50.2) :
    propriétés du document (mots-clés, commentaire, catégorie) et propriétés personnalisées
    (AIGenerated, AIProvider, AIModel, DigitalSourceType IPTC, date)."""
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from xml.sax.saxutils import escape
    cp = doc.core_properties
    cp.author = "Superviseur IA Comptable - SMD Global Consulting LLC"
    cp.category = "Contenu généré par IA"
    cp.keywords = "AI-generated; contenu généré par IA; Mistral AI; trainedAlgorithmicMedia"
    cp.comments = mention
    props = [("AIGenerated", "true"), ("AIProvider", "Mistral AI"), ("AIModel", modele or "non précisé"),
             ("AIGenerationDate", date_iso), ("DigitalSourceType", IPTC_IA),
             ("AISystem", "Superviseur IA Comptable (SMD Global Consulting LLC)"), ("AIDisclosure", mention)]
    corps = "".join(
        f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{n}">'
        f"<vt:lpwstr>{escape(v)}</vt:lpwstr></property>" for i, (n, v) in enumerate(props, start=2))
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' + corps + "</Properties>")
    paquet = doc.part.package
    part = Part(PackURI("/docProps/custom.xml"),
                "application/vnd.openxmlformats-officedocument.custom-properties+xml", xml.encode("utf-8"), paquet)
    paquet.relate_to(part, RT.CUSTOM_PROPERTIES)
    return doc


# ─── Typographie française ───────────────────────────────────────────────────
NBSP, NNBSP = "\u00a0", "\u202f"   # espace insécable, espace fine insécable


def typo_fr(texte: str) -> str:
    """Espaces insécables : avant « : » (insécable), avant « ; ! ? % € » (fine), dans « ... » et les milliers.
    Les adresses web (https://...) et les heures (10:30) ne sont pas touchées."""
    t = str(texte)
    t = re.sub(r"[ \u00a0\u202f]+:(?=\s|$)", NBSP + ":", t)
    t = re.sub(r"[ \u00a0\u202f]+([;!?])", NNBSP + r"\1", t)
    t = re.sub(r"(\d)[ \u00a0\u202f]*(%|€)", r"\1" + NNBSP + r"\2", t)
    t = re.sub(r"(?<!\d) - | - (?=\D)", " – ", t)   # tiret de séparation → tiret demi-cadratin (hors « 2025 - 2026 »)
    t = re.sub(r"«[ \u00a0\u202f]*", "«" + NNBSP, t)
    t = re.sub(r"[ \u00a0\u202f]*»", NNBSP + "»", t)
    t = re.sub(r"(?<![\d,.])(\d{1,3})((?:[ \u00a0\u202f]\d{3})+)(?![\d])",
               lambda m: m.group(1) + re.sub(r"[ \u00a0\u202f]", NNBSP, m.group(2)), t)
    return t


def nombres_fr(texte: str) -> str:
    """Rapports calculés par l'appli : 1,234.56 → 1 234,56 et 95.5 → 95,5 (hors adresses web).
    Non appliqué aux textes rédigés par l'IA, où « 1,250 » peut être un nombre décimal français."""
    def conv(seg):
        seg = re.sub(r"(?<![\d.,])([1-9]\d{0,2}(?:,\d{3})+)(\.\d+)?(?![\d,])",
                     lambda m: m.group(1).replace(",", NNBSP) + (m.group(2) or "").replace(".", ","), seg)
        return re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", r"\1,\2", seg)
    return "".join(x if "://" in x else conv(x) for x in re.split(r"(\S*://\S*)", str(texte)))


def titre_lisible(titre: str) -> str:
    """« Compte_Resultat_Entreprise » → « Compte Résultat Entreprise » (titre affiché, pas le nom de fichier)."""
    t = re.sub(r"[_]+", " ", str(titre or "")).strip()
    for a, b in (("Reponse", "Réponse"), ("Resultat", "Résultat"), ("Coherence", "Cohérence"),
                 ("Cloture", "Clôture"), ("Checklist", "Check-list")):
        t = re.sub(rf"\b{a}\b", b, t)
    return t[:1].upper() + t[1:] if t else "Rapport"


# ─── Conversion Markdown → Word ──────────────────────────────────────────────
_INLINE = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|__.+?__|(?<![\w*])\*(?!\s).+?(?<!\s)\*(?![\w*])|"
                     r"(?<![\w_])_(?!\s).+?(?<!\s)_(?![\w_])|`[^`]+`|~~.+?~~|\[[^\]]+\]\([^)]+\))")


def _runs(par, texte, gras=False, italique=False):
    """Ajoute le texte au paragraphe en interprétant **gras**, *italique*, `code`, ~~barré~~ et [lien](url)."""
    texte = re.sub(r"<br\s*/?>", "\n", texte).replace("\\*", "*").replace("\\_", "_")
    pos = 0
    for m in _INLINE.finditer(texte):
        if m.start() > pos:
            _run(par, texte[pos:m.start()], gras, italique)
        x = m.group(0)
        if x.startswith("***"):
            _runs(par, x[3:-3], True, True)
        elif x.startswith(("**", "__")):
            _runs(par, x[2:-2], True, italique)
        elif x.startswith(("*", "_")):
            _runs(par, x[1:-1], gras, True)
        elif x.startswith("`"):
            r = _run(par, x[1:-1], gras, italique)
            r.font.name = "Consolas"
        elif x.startswith("~~"):
            _run(par, x[2:-2], gras, italique).font.strike = True
        else:
            lib, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", x).groups()
            _run(par, lib, gras, italique)
            if url.strip() != lib.strip():
                _run(par, f" ({url})", gras, italique).font.color.rgb = RGBColor(31, 78, 121)
        pos = m.end()
    if pos < len(texte):
        _run(par, texte[pos:], gras, italique)


def _run(par, texte, gras, italique):
    r = par.add_run(texte if "://" in texte else typo_fr(texte))
    r.bold, r.italic = gras or None, italique or None
    return r


def _filet(doc):
    """Ligne de séparation (bordure basse d'un paragraphe vide), à la place de « --- »."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    p = doc.add_paragraph()
    bdr = OxmlElement("w:pBdr")
    bas = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "A6B4C8")):
        bas.set(qn(k), v)
    bdr.append(bas)
    p._p.get_or_add_pPr().append(bdr)


def _cellules(ligne):
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def largeurs_colonnes(rangs, n, utile=16.0):
    """Largeurs (cm) proportionnelles au texte le plus long de chaque colonne, bornées :
    une colonne longue ne dépasse pas 45 caractères de poids, une courte en garde au moins 6."""
    poids = []
    for j in range(n):
        lmax = max((len(str(r[j]).replace("**", "")) for r in rangs if j < len(r)), default=0)
        poids.append(min(max(lmax, 7), 45) + 2)   # + 2 : marges intérieures de la cellule
    total = sum(poids) or 1
    return [utile * p / total for p in poids]


def _tableau(doc, lignes):
    """Tableau Markdown (| a | b |) → tableau Word ; alignement à droite repris de |---:|."""
    rangs = [_cellules(l) for l in lignes]
    aligns = []
    if len(rangs) > 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in rangs[1] if c):
        aligns = ["droite" if c.endswith(":") and not c.startswith(":") else "centre" if c.startswith(":") and c.endswith(":")
                  else "gauche" if c.startswith(":") else "auto" for c in rangs[1]]
        rangs = [rangs[0]] + rangs[2:]
    n = max(len(r) for r in rangs)
    t = doc.add_table(rows=len(rangs), cols=n)
    t.style = "Table Grid"
    for i, r in enumerate(rangs):
        for j in range(n):
            cel = t.cell(i, j)
            par = cel.paragraphs[0]
            _runs(par, r[j] if j < len(r) else "", gras=(i == 0))
            a = aligns[j] if j < len(aligns) else "auto"
            if a == "auto":   # colonne chiffrée (toutes les valeurs sont des nombres) : à droite, en-tête compris
                vals = [x[j] for x in rangs[1:] if j < len(x) and x[j]]
                codes = vals and all(re.fullmatch(r"\d+", v) for v in vals)   # n° de compte, codes : à gauche
                a = "droite" if vals and not codes and all(re.fullmatch(r"[-+−]?[\d\s\u00a0\u202f.,]+\s*(%|€|EUR)?", v.replace("*", "")) for v in vals) else "gauche"
            par.alignment = {"droite": WD_ALIGN_PARAGRAPH.RIGHT, "centre": WD_ALIGN_PARAGRAPH.CENTER}.get(a, WD_ALIGN_PARAGRAPH.LEFT)
            for run in par.runs:
                run.font.size = Pt(9.5)
    from docx.shared import Cm
    from utils.word_visuels import largeurs, garder_ensemble
    largeurs(t, [Cm(c) for c in largeurs_colonnes(rangs, n)])
    if len(t.rows) <= 30:   # un tableau court ne se coupe pas entre deux pages
        garder_ensemble(t)
    doc.add_paragraph()


def ecrire_markdown(doc, texte, sauter_titre=None):
    """Écrit un texte Markdown dans le document Word avec une vraie mise en forme."""
    lignes = str(texte).replace("\r\n", "\n").split("\n")
    i, titre_saute = 0, False
    while i < len(lignes):
        brut = lignes[i]
        ligne = brut.strip()
        if not ligne:
            i += 1
            continue
        if ligne.startswith("|"):
            bloc = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                bloc.append(lignes[i])
                i += 1
            _tableau(doc, bloc)
            continue
        i += 1
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", ligne)
        if m:
            niveau, txt = len(m.group(1)), m.group(2).replace("**", "")
            if sauter_titre and not titre_saute and niveau == 1 and txt == sauter_titre:
                titre_saute = True
                continue
            h = doc.add_heading(level=min(niveau, 4))
            _runs(h, txt)
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,}|={3,})", ligne):
            _filet(doc)
            continue
        m = re.match(r"^(\s*)([-*+•])\s+(.*)$", brut)
        if m:
            niv = min(len(m.group(1).replace("\t", "  ")) // 2, 2)
            p = doc.add_paragraph(style="List Bullet" + (f" {niv + 1}" if niv else ""))
            _runs(p, m.group(3))
            continue
        m = re.match(r"^(\s*)(\d{1,3})[.)]\s+(.*)$", brut)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18 + 12 * min(len(m.group(1)) // 2, 2))
            p.paragraph_format.first_line_indent = Pt(-18)
            _runs(p, f"{m.group(2)}.\t{m.group(3)}")
            p.paragraph_format.tab_stops.add_tab_stop(p.paragraph_format.left_indent)
            continue
        if ligne.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            _runs(p, ligne.lstrip("> "), italique=True)
            continue
        p = doc.add_paragraph()
        _runs(p, ligne)


def document_smd():
    """Document Word aux couleurs SMD : A4, police Segoe UI 11, en-tête et pied de page."""
    from datetime import datetime
    from docx.shared import Cm
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Segoe UI"
    style.font.size = Pt(11)
    section = doc.sections[0]
    # Format A4 (le modèle par défaut est au format Letter américain)
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.5)
    section.top_margin = section.bottom_margin = Cm(2.5)
    p = section.header.paragraphs[0]
    run_header = p.add_run("SMD Global Consulting LLC | Superviseur IA Comptable")
    run_header.font.color.rgb = RGBColor(31, 119, 180)
    run_header.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p = section.footer.paragraphs[0]
    f_p.text = typo_fr(f"Document confidentiel généré par SMD Global Consulting LLC – © {datetime.now().year}")
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return doc


_SIGNATURE = re.compile(r"^\*?\s*((Rapport|Analyse)\s+généré(e)?\s+par\s+)?SMD Global Consulting LLC\s*[-–—]\s*"
                        r"Superviseur IA Comptable\s*\*?$", re.I)


def _sans_signature(texte):
    """Retire la signature de fin de rapport (et le filet qui la précède) : l'en-tête et le pied de page
    du document Word portent déjà le nom de SMD Global Consulting LLC."""
    lignes = str(texte).rstrip().split("\n")
    for k in range(len(lignes) - 1, max(len(lignes) - 4, -1), -1):   # parmi les 3 dernières lignes
        if _SIGNATURE.match(lignes[k].strip()):
            fin = [l for l in lignes[k + 1:] if not re.match(r"^\*?\s*©", l.strip())]   # © : déjà en pied de page
            lignes = lignes[:k]
            while lignes and (not lignes[-1].strip() or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", lignes[-1].strip())):
                lignes.pop()
            if fin:
                lignes += [""] + fin
            break
    return "\n".join(lignes)


def _titre_nu(texte):
    """Titre sans emoji ni ponctuation de tête, en majuscules : « 📊 Synthèse exécutive » → « SYNTHÈSE EXÉCUTIVE »."""
    return re.sub(r"^[^\wÀ-ÿ]+", "", texte.replace("**", "")).strip().upper()


def _retirer_sections(texte, titres):
    """Retire du Markdown les sections dont le titre figure dans « titres » (déjà présentées par les indicateurs) :
    du titre jusqu'au titre suivant de même niveau ou de niveau supérieur."""
    cibles = {_titre_nu(t) for t in titres}
    sortie, niveau_coupe = [], None
    for ligne in str(texte).split("\n"):
        m = re.match(r"^\s*(#{1,6})\s+(.*?)\s*#*\s*$", ligne)
        if m:
            niveau = len(m.group(1))
            if niveau_coupe is not None and niveau <= niveau_coupe:
                niveau_coupe = None
            if niveau_coupe is None and _titre_nu(m.group(2)) in cibles:
                niveau_coupe = niveau
                continue
        if niveau_coupe is None:
            sortie.append(ligne)
    return "\n".join(sortie)


def _separer_chapeau(texte):
    """Sépare l'en-tête du rapport du reste, pour placer les indicateurs et graphiques juste après.
    En-tête : titre « # » ; juste après, un sous-titre « ## » éventuellement suivi d'une ligne « ### » ;
    puis lignes en italique, lignes « **Libellé** : valeur » et lignes vides ; un filet « --- » le clôt."""
    lignes = str(texte).split("\n")
    i, etape = 0, "titre"          # titre → sous_titre → precision → corps de l'en-tête
    while i < len(lignes):
        l = lignes[i].strip()
        if not l or re.match(r"^#\s", l):
            i += 1
        elif l.startswith("## ") and etape == "titre":
            etape, i = "sous_titre", i + 1
        elif l.startswith("### ") and etape == "sous_titre":
            etape, i = "precision", i + 1
        elif re.fullmatch(r"\*[^*].*\*", l) or re.match(r"^\*\*[^*]{1,40}\*\*\s*:", l):
            etape, i = "corps", i + 1
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", l):
            i += 1
            break
        else:
            break
    return "\n".join(lignes[:i]), "\n".join(lignes[i:])


def _retirer_paragraphes_vides_finaux(doc):
    """Supprime les paragraphes vides en fin de document : ils peuvent créer une dernière page blanche."""
    corps = doc.element.body
    while True:
        derniers = [e for e in corps if e.tag.endswith("}p") or e.tag.endswith("}tbl")]
        if not derniers or not derniers[-1].tag.endswith("}p"):
            break
        p = derniers[-1]
        texte = "".join(t.text or "" for t in p.iter() if t.tag.endswith("}t"))
        if texte.strip() or any(e.tag.endswith("}drawing") for e in p.iter()):
            break
        corps.remove(p)


def export_analyse_word(titre_analyse, contenu_texte, nom_client="", exercice="", ia=None,
                        indicateurs=None, graphiques=None, sans_sections=()):
    """ia : None pour un contenu calculé par règles ; sinon dict {"mention", "modele", "date"} pour un texte rédigé par IA.
    indicateurs : liste de dict {libelle, valeur, detail?, ton?} affichés en tête (voir word_visuels.bloc_indicateurs).
    graphiques : liste d'images PNG (bytes) placées après les indicateurs.
    sans_sections : titres de sections du texte à ne pas reprendre (déjà présentées par les indicateurs)."""
    doc = document_smd()

    contenu_texte = str(contenu_texte) if ia else nombres_fr(contenu_texte)
    # Titre : le premier titre « # … » du rapport s'il existe, sinon le titre lisible du bouton
    m = re.search(r"(?m)^#\s+(.+?)\s*$", contenu_texte)
    titre = m.group(1).replace("**", "").strip() if m else titre_lisible(titre_analyse)
    t = doc.add_heading(level=0)
    _runs(t, titre)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Client et exercice : affichés seulement s'ils sont connus
    infos = [x for x in (f"Client : {nom_client}" if nom_client else "",
                         f"Exercice : {exercice}" if exercice else "") if x]
    if infos:
        p = doc.add_paragraph()
        _runs(p, "   ·   ".join(infos))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    corps = _sans_signature(contenu_texte)
    if sans_sections:
        corps = _retirer_sections(corps, sans_sections)
    if indicateurs or graphiques:
        from utils.word_visuels import bloc_indicateurs, inserer_graphique
        chapeau, corps = _separer_chapeau(corps)
        ecrire_markdown(doc, chapeau, sauter_titre=titre if m else None)
        if indicateurs:
            bloc_indicateurs(doc, indicateurs)
        for png in graphiques or []:
            inserer_graphique(doc, png)
        ecrire_markdown(doc, corps)
    else:
        ecrire_markdown(doc, corps, sauter_titre=titre if m else None)

    if ia:
        marquer_docx_ia(doc, ia.get("mention", ""), ia.get("modele", ""), ia.get("date", ""))

    _retirer_paragraphes_vides_finaux(doc)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
