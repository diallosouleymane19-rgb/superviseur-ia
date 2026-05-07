from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

def export_analyse_word(titre_analyse, contenu_texte, nom_client="", exercice=""):
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
    run_header = p.add_run("SMD CONSULTING | Superviseur IA")
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
    f_p.text = "Document confidentiel généré par SMD Consulting - © 2026"
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Sauvegarde en mémoire pour le téléchargement Streamlit
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
