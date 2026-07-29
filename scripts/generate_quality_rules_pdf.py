"""Generate quality_rules.pdf from documentation"""
from fpdf import FPDF
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
OUTPUT = os.path.join(DOCS_DIR, "quality_rules.pdf")


class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Regles de Qualite des Donnees", align="R", new_x="LMARGIN", new_y="NEXT")
            self.line(10, 15, 200, 15)
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def title_page(self, title):
        self.ln(8)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(41, 128, 185)
        self.cell(0, 12, title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(41, 128, 185)
        self.line(40, self.get_y(), 170, self.get_y())
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(41, 128, 185)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def rule_row(self, num, col, desc, sev, expected, fill):
        self.set_fill_color(240, 245, 250) if fill else self.set_fill_color(255, 255, 255)
        self.set_font("Helvetica", "", 8)
        h = 6
        self.cell(7, h, str(num), border=1, fill=True, align="C")
        self.cell(30, h, col, border=1, fill=True)
        self.cell(75, h, desc[:74], border=1, fill=True)
        self.cell(18, h, sev, border=1, fill=True, align="C")
        self.cell(50, h, expected[:48], border=1, fill=True)
        self.ln()

    def rule_table(self, rules):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(52, 152, 219)
        self.set_text_color(255, 255, 255)
        headers = ["#", "Colonne", "Description", "Severite", "Valeur Attendue"]
        widths = [7, 30, 75, 18, 50]
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)
        for i, r in enumerate(rules):
            self.rule_row(r[0], r[1], r[2], r[3], r[4], i % 2 == 0)

    def explanation(self, num, title, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(41, 128, 185)
        self.cell(0, 6, f"Regle {num} - {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(0, 4.5, text)


pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

pdf.title_page("Regles de Qualite des Donnees")
pdf.set_font("Helvetica", "", 9)
pdf.cell(0, 6, "Data Governance & Accuracy Project", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "CoreBanking - Data Quality Framework", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)

pdf.set_font("Helvetica", "", 8)
pdf.multi_cell(0, 4.5, (
    "Ce document decrit l'ensemble des regles de qualite des donnees appliquees par le pipeline ETL "
    "sur les donnees bancaires. Chaque regle est accompagnee d'une explication et de la severite associee. "
    "Les regles sont organisees par domaine : Client, Compte, Transaction Bancaire et Credit."
))
pdf.ln(4)

# === CLIENT ===
pdf.section_title("1. Client")
rules = [
    (1, "CIN", "Le CIN doit contenir exactement 8 chiffres", "Haute", "8 digits"),
    (2, "Telephone", "Doit commencer par +216/00216 + 8 chiffres", "Haute", "+216/00216 + 8 d"),
    (3, "Email", "Doit respecter le format user@domain.ext", "Moyenne", "Email valide"),
    (4, "Date_Naissance", "Pas future, pas avant 1900, age >= 18", "Haute", "1900 -> -18 ans"),
    (5, "Ville", "Si adresse fournie, ville requise", "Moyenne", "Ville requise"),
    (6, "Date_Naissance", "Client Entreprise/Cooperative >= 18 ans", "Haute", "18+ pour co./ent."),
]
pdf.rule_table(rules)
pdf.ln(4)

explanations = [
    ("Format CIN Tunisien", "Le CIN tunisien est un identifiant national unique de 8 chiffres. Toute valeur contenant des lettres ou un nombre de chiffres different est consideree comme erronee."),
    ("Format Telephone Tunisien", "Les numeros de telephone tunisiens valides commencent par l'indicatif +216 ou 00216 suivis de 8 chiffres (ex: +21699123456). Les numeros etrangers ou formats incorrects sont signales."),
    ("Format Email", "Verifie que l'email contient un @ et un nom de domaine avec extension (ex: user@domain.com). Les emails sans @ ou sans extension sont rejetes."),
    ("Date de Naissance Valide", "Verifie la plausibilite de la date : pas de date future, pas de date avant 1900, et age minimum de 18 ans pour etre titulaire d'un compte bancaire."),
    ("Ville Manquante", "Cohérence geographique : si une adresse physique est fournie, la ville doit egalement etre renseignee pour permettre la localisation."),
    ("Cohérence Age / Type Client", "Une entreprise ou cooperative est necessairement geree par une personne majeure. Un client enregistre comme Entreprise ou Cooperative mais age de moins de 18 ans est une incohérence."),
]
for i, (t, txt) in enumerate(explanations, 1):
    pdf.explanation(i, t, txt)

# === COMPTE ===
pdf.add_page()
pdf.section_title("2. Compte")
rules = [
    (1, "Solde", "Solde ne depasse pas 1Md, mini 0.01 (sauf 0)", "Haute", "-1B a 1B"),
    (2, "Solde", "Maximum 3 decimales (precision monetaire)", "Moyenne", "3 decimales max"),
    (3, "Date_Ouverture", "Pas future, pas avant 1950", "Haute", "1950 -> today"),
    (4, "Statut", "Compte cloture = solde zero", "Haute", "Clos = 0"),
    (5, "Numero_Compte", "Au moins 10 caracteres", "Moyenne", ">= 10 car."),
    (6, "Client_ID", "Chaque compte doit avoir un client", "Haute", "Client requis"),
]
pdf.rule_table(rules)
pdf.ln(4)

explanations = [
    ("Solde Extreme", "Les soldes extremes (>= 1Md) ou anormalement bas (entre 0 et 0.01) indiquent probablement des erreurs de saisie ou des anomalies."),
    ("Precision Decimale du Solde", "Les montants monetaires sont limites a 3 decimales. Au-dela, il s'agit probablement d'une erreur d'arrondi ou de saisie."),
    ("Date d'Ouverture Valide", "La banque n'existait pas avant 1950, et une date d'ouverture future est impossible. La date doit etre dans l'intervalle plausible."),
    ("Cohérence Statut / Solde", "Regle metier : un compte clos ne devrait pas avoir de solde restant. Cela indique que le compte n'a pas ete correctement finalise."),
    ("Format Numero de Compte", "Les numeros de compte bancaires suivent un format standard d'au moins 10 caracteres. Un numero trop court est suspect."),
    ("Compte sans Client", "Tout compte doit etre associe a un client. Un compte orphelin est une anomalie de referentiel."),
]
for i, (t, txt) in enumerate(explanations, 1):
    pdf.explanation(i, t, txt)

# === TRANSACTION ===
pdf.add_page()
pdf.section_title("3. Transaction Bancaire")
rules = [
    (1, "Montant", "Montant ne depasse pas 100M", "Haute", "-100M a 100M"),
    (2, "Montant", "Maximum 3 decimales", "Moyenne", "3 decimales max"),
    (3, "Date_Transaction", "Entre 2000 et aujourd'hui", "Haute", "2000 -> today"),
    (4, "Montant", "Virement doit avoir montant > 0", "Haute", "Virement > 0"),
    (5, "Reference_Transaction", "Chaque transaction doit avoir une reference", "Moyenne", "Reference req."),
    (6, "Compte_ID", "Pas de transaction sur compte clos", "Haute", "Compte actif"),
]
pdf.rule_table(rules)
pdf.ln(4)

explanations = [
    ("Montant Extreme", "Une transaction de plus de 100M est consideree comme extreme et potentiellement erronee."),
    ("Precision Decimale", "Pas plus de 3 decimales pour un montant monetaire, meme regle que pour les soldes."),
    ("Date de Transaction Valide", "Les transactions avant l'an 2000 ou dans le futur sont invalides. La date doit etre dans l'intervalle acceptable."),
    ("Cohérence Type / Montant", "Un virement ne peut pas avoir un montant negatif ou nul par nature. Cela indique une erreur de saisie."),
    ("Transaction sans Reference", "Toute transaction doit avoir une reference unique pour assurer la tracabilite et l'audit."),
    ("Transaction sur Compte Cloture", "Un compte clos ne peut plus recevoir de transactions. C'est une regle metier fondamentale de securite."),
]
for i, (t, txt) in enumerate(explanations, 1):
    pdf.explanation(i, t, txt)

# === CREDIT ===
pdf.add_page()
pdf.section_title("4. Credit")
rules = [
    (1, "Montant", "Montant entre 100 et 10M", "Haute", "100 a 10M"),
    (2, "Montant", "Maximum 3 decimales", "Moyenne", "3 decimales max"),
    (3, "Taux_Interet", "Taux entre 2% et 25% (Tunisie)", "Haute", "2% a 25%"),
    (4, "Date_Debut", "Pas future, pas avant 2000", "Haute", "2000 -> today"),
    (5, "Montant", "Mensualite (montant/duree) >= 10", "Haute", "Mensualite >= 10"),
    (6, "Client_ID", "Chaque credit doit avoir un client", "Haute", "Client requis"),
    (7, "Duree_Mois", "Entre 1 et 360 mois (30 ans max)", "Haute", "1 a 360 mois"),
]
pdf.rule_table(rules)
pdf.ln(4)

explanations = [
    ("Montant Extreme", "Un credit de moins de 100 ou de plus de 10M est considere comme extreme et potentiellement errone."),
    ("Precision Decimale", "Pas plus de 3 decimales pour un montant monetaire."),
    ("Taux d'Interet Hors Plage", "Les taux d'interet sur le marche tunisien sont generalement compris entre 2% et 25%. En dehors de cette fourchette, il s'agit probablement d'une erreur."),
    ("Date de Debut Valide", "Un credit ne peut pas avoir une date de debut avant 2000 (marche moderne) ni dans le futur."),
    ("Cohérence Montant / Duree", "La mensualite estimee (montant total / duree en mois) doit etre realiste. Une mensualite inferieure a 10 est suspecte."),
    ("Credit sans Client", "Tout credit doit etre associe a un client. Un credit orphelin est une anomalie de referentiel."),
    ("Duree Anormale", "La duree d'un credit ne peut pas depasser 30 ans (360 mois) ni etre inferieure a 1 mois."),
]
for i, (t, txt) in enumerate(explanations, 1):
    pdf.explanation(i, t, txt)

pdf.output(OUTPUT)
print(f"PDF generated: {OUTPUT}")
