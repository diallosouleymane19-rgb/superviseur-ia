# -*- coding: utf-8 -*-
"""
Lecture des factures électroniques structurées (réforme 2026) - SMD Global Consulting LLC
  - CII (UN/CEFACT CrossIndustryInvoice) : XML seul ou embarqué dans un PDF Factur-X
  - UBL 2.1 (Invoice / CreditNote)
Les données sont lues directement dans le XML (montants exacts, aucune OCR, aucune API)
et restituées au format du moteur utils/compta_facture.py.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# Noms des fichiers XML joints à un PDF Factur-X / ZUGFeRD / XRechnung
NOMS_XML_PDF = ("factur-x.xml", "zugferd-invoice.xml", "xrechnung.xml", "zugferd_invoice.xml")

PAYS_UE_ISO = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "EL", "HR", "HU",
               "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}

# Catégories de TVA (UNTDID 5305) utilisées par la norme EN 16931
CATEGORIES_TVA = {
    "S": "taux normal ou réduit", "Z": "taux zéro", "E": "exonération", "AE": "autoliquidation",
    "K": "livraison intracommunautaire", "G": "exportation hors UE", "O": "hors champ de la TVA",
    "L": "Canaries", "M": "Ceuta et Melilla",
}


def _ln(tag):
    return tag.rsplit("}", 1)[-1]


def _enfants(e, nom):
    return [c for c in list(e) if _ln(c.tag) == nom] if e is not None else []


def _enfant(e, *chemin):
    """Premier élément au bout du chemin (noms locaux, sans espaces de noms)."""
    for nom in chemin:
        if e is None:
            return None
        e = next((c for c in list(e) if _ln(c.tag) == nom), None)
    return e


def _txt(e, *chemin):
    x = _enfant(e, *chemin)
    return (x.text or "").strip() if x is not None and x.text else ""


def _num(e, *chemin):
    t = _txt(e, *chemin)
    try:
        return round(float(t), 2) if t else None
    except ValueError:
        return None


def _tous(e, nom):
    """Tous les descendants portant ce nom local."""
    return [x for x in e.iter() if _ln(x.tag) == nom] if e is not None else []


def _id_schema(e, nom, schema):
    for x in _enfants(e, nom):
        if x.get("schemeID") == schema and x.text:
            return x.text.strip()
    return ""


def _date(txt):
    t = (txt or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(t[:10] if "-" in t else t[:8], fmt)
        except ValueError:
            continue
    return None


def _siren(txt):
    d = re.sub(r"\D", "", txt or "")
    return d[:9] if len(d) >= 9 else ""


def format_xml(racine):
    """'CII', 'UBL' ou '' selon l'élément racine."""
    nom = _ln(racine.tag)
    if nom == "CrossIndustryInvoice":
        return "CII"
    if nom in ("Invoice", "CreditNote"):
        return "UBL"
    return ""


def xml_depuis_pdf(contenu: bytes):
    """XML Factur-X joint au PDF (ou None)."""
    try:
        import pymupdf
        with pymupdf.open(stream=contenu, filetype="pdf") as doc:
            noms = doc.embfile_names()
            cible = next((n for n in noms if n.lower() in NOMS_XML_PDF), None) \
                or next((n for n in noms if n.lower().endswith(".xml")), None)
            return doc.embfile_get(cible) if cible else None
    except Exception:
        return None


def _base(source, fmt):
    return {"source": source, "structure": fmt, "type": None, "numero": "", "date": None,
            "fournisseur": "", "client": "", "objet": "", "siren": "", "siren_client": "",
            "categorie": "", "adresse_livraison": False, "tva_intra": "", "adresse": False,
            "ht": None, "tva": None, "ttc": None, "lignes_tva": [], "autoliquidation": False,
            "franchise": False, "option_debits": False, "exoneration": False, "devise": "EUR",
            "etranger": False, "hors_ue": False, "pays_hors_ue": "", "pays_ue": "", "categories_tva": []}


def _cadre(code):
    """BT-23 (cadre de facturation, ex. S1, B1, M1) -> catégorie d'opération LB / PS / LBPS."""
    c = (code or "").strip().upper()[:1]
    return {"B": "LB", "S": "PS", "M": "LBPS"}.get(c, "")


def _pays(d, code_pays):
    code = (code_pays or "").upper()
    d["pays_code"] = code
    if code and code != "FR":
        d["etranger"] = True
        if code in PAYS_UE_ISO:
            d["pays_ue"] = code
        else:
            d["hors_ue"], d["pays_hors_ue"] = True, code


def _regime_tva(d, taxes, notes):
    """Catégories de TVA -> drapeaux du moteur (autoliquidation, exonération, franchise)."""
    cats = sorted({t["categorie"] for t in taxes if t["categorie"]})
    d["categories_tva"] = cats
    raisons = " ".join(t.get("raison", "") for t in taxes).lower() + " " + notes.lower()
    if cats and set(cats) <= {"AE", "K"}:
        d["autoliquidation"] = True
    if cats and set(cats) <= {"E", "G", "O", "Z"} and not any(t["montant"] for t in taxes):
        if re.search(r"293\s?b|franchise", raisons):
            d["franchise"] = True
        else:
            d["exoneration"] = True
    if re.search(r"d.apr[eè]s les d[ée]bits", raisons):
        d["option_debits"] = True


def lire_cii(racine, source):
    d = _base(source, "CII")
    ctx = _enfant(racine, "ExchangedDocumentContext")
    doc = _enfant(racine, "ExchangedDocument")
    tr = _enfant(racine, "SupplyChainTradeTransaction")
    accord = _enfant(tr, "ApplicableHeaderTradeAgreement")
    livr = _enfant(tr, "ApplicableHeaderTradeDelivery")
    regl = _enfant(tr, "ApplicableHeaderTradeSettlement")
    tot = _enfant(regl, "SpecifiedTradeSettlementHeaderMonetarySummation")

    d["categorie"] = _cadre(_txt(ctx, "BusinessProcessSpecifiedDocumentContextParameter", "ID"))
    d["profil"] = _txt(ctx, "GuidelineSpecifiedDocumentContextParameter", "ID")
    d["numero"] = _txt(doc, "ID")
    code = _txt(doc, "TypeCode")
    d["type_code"] = code
    d["type"] = "avoir" if code in ("381", "261", "262", "396", "502", "503") else "facture"
    d["date"] = _date(_txt(doc, "IssueDateTime", "DateTimeString"))
    notes = "\n".join(_txt(n, "Content") for n in _enfants(doc, "IncludedNote"))

    vend, ach = _enfant(accord, "SellerTradeParty"), _enfant(accord, "BuyerTradeParty")
    d["fournisseur"] = _txt(vend, "Name")
    d["client"] = _txt(ach, "Name")
    d["siren"] = _siren(_id_schema(_enfant(vend, "SpecifiedLegalOrganization"), "ID", "0002")) \
        or _siren(_id_schema(vend, "GlobalID", "0009"))
    d["siren_client"] = _siren(_id_schema(_enfant(ach, "SpecifiedLegalOrganization"), "ID", "0002")) \
        or _siren(_id_schema(ach, "GlobalID", "0009"))
    for reg in _enfants(vend, "SpecifiedTaxRegistration"):
        x = _enfant(reg, "ID")
        if x is not None and x.get("schemeID") == "VA":
            d["tva_intra"] = re.sub(r"\s", "", x.text or "")
    adr = _enfant(vend, "PostalTradeAddress")
    d["adresse"] = bool(_txt(adr, "CityName") or _txt(adr, "LineOne"))
    _pays(d, _txt(adr, "CountryID"))
    d["adresse_livraison"] = _enfant(livr, "ShipToTradeParty") is not None

    lignes = []
    for li in _enfants(tr, "IncludedSupplyChainTradeLineItem"):
        nom = _txt(li, "SpecifiedTradeProduct", "Name")
        desc = _txt(li, "SpecifiedTradeProduct", "Description")
        lignes.append(nom + (f" ({desc})" if desc and desc.lower() != "description" else ""))
        cpt = _txt(li, "SpecifiedLineTradeSettlement", "ReceivableSpecifiedTradeAccountingAccount", "ID")
        if re.fullmatch(r"[1-7]\d{5}", cpt) and not d.get("compte_acheteur"):
            d["compte_acheteur"] = cpt
    d["objet"] = " ; ".join(x for x in lignes if x)[:200]

    d["devise"] = _txt(regl, "InvoiceCurrencyCode") or "EUR"
    taxes = []
    for t in _enfants(regl, "ApplicableTradeTax"):
        taxes.append({"categorie": _txt(t, "CategoryCode"), "taux": _num(t, "RateApplicablePercent"),
                      "montant": _num(t, "CalculatedAmount") or 0.0, "base": _num(t, "BasisAmount"),
                      "raison": _txt(t, "ExemptionReason"), "exigibilite": _txt(t, "DueDateTypeCode")})
    _regime_tva(d, taxes, notes)
    if any(t["exigibilite"] == "5" for t in taxes):   # BT-8 = date de facture : option pour les débits
        d["option_debits"] = True
    d["lignes_tva"] = [{"taux": t["taux"], "montant": t["montant"]} for t in taxes if t["montant"]]
    d["detail_tva"] = taxes

    d["ht"] = _num(tot, "TaxBasisTotalAmount")
    tva_eur = [x for x in _enfants(tot, "TaxTotalAmount") if (x.get("currencyID") or d["devise"]) == d["devise"]]
    d["tva"] = round(float(tva_eur[0].text), 2) if tva_eur and tva_eur[0].text else \
        round(sum(t["montant"] for t in taxes), 2)
    d["ttc"] = _num(tot, "GrandTotalAmount")
    d["net_a_payer"] = _num(tot, "DuePayableAmount")
    d["texte"] = "\n".join([d["fournisseur"], d["objet"], notes])
    return d


def lire_ubl(racine, source):
    d = _base(source, "UBL")
    avoir = _ln(racine.tag) == "CreditNote"
    d["categorie"] = _cadre(_txt(racine, "ProfileID"))
    d["profil"] = _txt(racine, "CustomizationID")
    d["numero"] = _txt(racine, "ID")
    code = _txt(racine, "CreditNoteTypeCode" if avoir else "InvoiceTypeCode")
    d["type_code"] = code
    d["type"] = "avoir" if avoir or code in ("381", "261", "262", "396") else "facture"
    d["date"] = _date(_txt(racine, "IssueDate"))
    notes = "\n".join(re.sub(r"^#\w+#", "", (n.text or "").strip()) for n in _enfants(racine, "Note"))

    def partie(nom):
        return _enfant(racine, nom, "Party")
    vend, ach = partie("AccountingSupplierParty"), partie("AccountingCustomerParty")

    def nom_partie(p):
        return _txt(p, "PartyLegalEntity", "RegistrationName") or _txt(p, "PartyName", "Name")
    d["fournisseur"], d["client"] = nom_partie(vend), nom_partie(ach)
    d["siren"] = _siren(_id_schema(_enfant(vend, "PartyLegalEntity"), "CompanyID", "0002"))
    d["siren_client"] = _siren(_id_schema(_enfant(ach, "PartyLegalEntity"), "CompanyID", "0002"))
    for pts in _enfants(vend, "PartyTaxScheme"):
        if _txt(pts, "TaxScheme", "ID") == "VAT":
            d["tva_intra"] = re.sub(r"\s", "", _txt(pts, "CompanyID"))
    adr = _enfant(vend, "PostalAddress")
    d["adresse"] = bool(_txt(adr, "CityName") or _txt(adr, "StreetName"))
    _pays(d, _txt(adr, "Country", "IdentificationCode"))
    d["adresse_livraison"] = _enfant(racine, "Delivery", "DeliveryLocation") is not None

    lignes = []
    for li in _enfants(racine, "CreditNoteLine" if avoir else "InvoiceLine"):
        lignes.append(_txt(li, "Item", "Name") or _txt(li, "Item", "Description"))
        cpt = _txt(li, "AccountingCost")
        if re.fullmatch(r"[1-7]\d{5}", cpt) and not d.get("compte_acheteur"):
            d["compte_acheteur"] = cpt
    d["objet"] = " ; ".join(x for x in lignes if x)[:200]

    d["devise"] = _txt(racine, "DocumentCurrencyCode") or "EUR"
    taxes = []
    for tt in _enfants(racine, "TaxTotal"):
        for st in _enfants(tt, "TaxSubtotal"):
            if (_enfant(st, "TaxAmount") is not None and
                    (_enfant(st, "TaxAmount").get("currencyID") or d["devise"]) != d["devise"]):
                continue
            taxes.append({"categorie": _txt(st, "TaxCategory", "ID"), "taux": _num(st, "TaxCategory", "Percent"),
                          "montant": _num(st, "TaxAmount") or 0.0, "base": _num(st, "TaxableAmount"),
                          "raison": _txt(st, "TaxCategory", "TaxExemptionReason")})
    _regime_tva(d, taxes, notes)
    if _txt(racine, "InvoicePeriod", "DescriptionCode") == "3":   # BT-8 = date de facture : option débits
        d["option_debits"] = True
    d["lignes_tva"] = [{"taux": t["taux"], "montant": t["montant"]} for t in taxes if t["montant"]]
    d["detail_tva"] = taxes

    tot = _enfant(racine, "LegalMonetaryTotal")
    d["ht"] = _num(tot, "TaxExclusiveAmount")
    tva = [x for x in _enfants(racine, "TaxTotal")
           if _enfant(x, "TaxAmount") is not None and (_enfant(x, "TaxAmount").get("currencyID") or d["devise"]) == d["devise"]]
    d["tva"] = _num(tva[0], "TaxAmount") if tva else round(sum(t["montant"] for t in taxes), 2)
    d["ttc"] = _num(tot, "TaxInclusiveAmount")
    d["net_a_payer"] = _num(tot, "PayableAmount")
    d["texte"] = "\n".join([d["fournisseur"], d["objet"], notes])
    return d


def lire_facture_xml(contenu: bytes, source: str):
    """Retourne (données, message) ; données = None si le XML n'est pas une facture CII / UBL."""
    try:
        racine = ET.fromstring(contenu)
    except ET.ParseError as e:
        return None, f"{source} : XML illisible ({e})"
    fmt = format_xml(racine)
    if not fmt:
        return None, f"{source} : XML non reconnu comme facture (ni CII, ni UBL)"
    d = lire_cii(racine, source) if fmt == "CII" else lire_ubl(racine, source)
    if d["tva"] is None and d["ht"] is not None and d["ttc"] is not None:
        d["tva"] = round(d["ttc"] - d["ht"], 2)
    return d, ""
