from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

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


def export_analyse_word(titre_analyse, contenu_texte, nom_client="", exercice="", ia=None):
    """ia : None pour un contenu calculé par règles ; sinon dict {"mention", "modele", "date"} pour un texte rédigé par IA."""
    doc = Document()
    
    # --- STYLE GLOBAL (Police et taille) ---
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Segoe UI'
    font.size = Pt(11)

    # --- EN-TÊTE CORPORATE ---
    section = doc.sections[0]
    header = section.header
    p = header.paragraphs[0]
    # Signature de votre cabinet
    run_header = p.add_run("SMD Global Consulting LLC | Superviseur IA")
    run_header.font.color.rgb = RGBColor(31, 119, 180) # Bleu institutionnel
    run_header.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # --- TITRE DU RAPPORT ---
    doc.add_paragraph("\n")
    t = doc.add_heading(titre_analyse, 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # --- INFOS CLIENT (Tableau discret) ---
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    cells = table.rows[0].cells
    cells[0].text = f"Client : {nom_client if nom_client else 'Client SMD'}"
    cells[1].text = f"Exercice : {exercice if exercice else '2024'}"
    doc.add_paragraph("\n")

    # --- TRAITEMENT DU CONTENU ---
    # Cette étape est cruciale pour éviter les erreurs de plantage (AttributeError)
    contenu_texte = str(contenu_texte)
    
    for line in contenu_texte.split('\n'):
        line = line.strip()
        if not line: continue
            
        if line.startswith('###'):
            doc.add_heading(line.replace('###', '').strip(), level=2)
        elif line.startswith('##'):
            doc.add_heading(line.replace('##', '').strip(), level=1)
        elif line.startswith('**') and line.endswith('**'):
            p = doc.add_paragraph()
            p.add_run(line.replace('**', '').strip()).bold = True
        else:
            p = doc.add_paragraph(line.replace('**', ''))

    # --- PIED DE PAGE ---
    footer = section.footer
    f_p = footer.paragraphs[0]
    f_p.text = "Document confidentiel généré par SMD Global Consulting LLC - © 2026"
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if ia:
        marquer_docx_ia(doc, ia.get("mention", ""), ia.get("modele", ""), ia.get("date", ""))

    # Sauvegarde en mémoire pour le téléchargement Streamlit
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
