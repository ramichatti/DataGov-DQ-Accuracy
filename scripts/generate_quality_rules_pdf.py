"""Generate PDF documentation of accuracy quality rules"""
from fpdf import FPDF
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

rules = {
    "Client": [
        ("CIN", "8 digits (Tunisian format)", "LEN(CIN) <> 8 OR ISNUMERIC(CIN) = 0", "High"),
        ("Telephone", "+216/00216 + 8 digits", "NOT(REPLACE(Tel,'+','') LIKE '216%' AND LEN=11)", "High"),
        ("Email", "user@domain.extension", "Email NOT LIKE '%_@__%.__%'", "Medium"),
        ("Date_Naissance", "1900-01-01 to 18 years ago", "Future OR <1900 OR age<18", "High"),
    ],
    "Compte": [
        ("Solde", "Between -1B and 1B", "ABS(Solde) > 1000000000", "High"),
        ("Date_Ouverture", "1950-01-01 to current date", "Future OR < 1950-01-01", "High"),
        ("Statut", "Closed = zero balance", "Statut='Cloture' AND Solde<>0", "High"),
    ],
    "Transaction": [
        ("Montant", "Between -100M and 100M", "ABS(Montant) > 100000000", "High"),
        ("Date_Transaction", "2000-01-01 to current date", "Future OR < 2000-01-01", "High"),
    ],
    "Credit": [
        ("Montant", "Between 100 and 10M", "ABS(Montant)>10M OR (ABS<100 AND <>0)", "High"),
        ("Taux_Interet", "Between 2% and 25%", "Taux<2 OR Taux>25", "High"),
        ("Date_Debut", "2000-01-01 to current date", "Future OR < 2000-01-01", "High"),
    ],
}

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Data Quality - Accuracy Rules", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

for domain, cols in rules.items():
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, f"  {domain}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    col_w = [32, 50, 82, 16]
    headers = ["Column", "Expected", "Detection Logic", "Sev."]
    for h, w in zip(headers, col_w):
        pdf.cell(w, 7, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for col, expected, logic, sev in cols:
        pdf.cell(col_w[0], 6, col, border=1)
        pdf.cell(col_w[1], 6, expected, border=1)
        pdf.cell(col_w[2], 6, logic, border=1)
        pdf.cell(col_w[3], 6, sev, border=1, align="C")
        pdf.ln()

    pdf.ln(5)

os.makedirs(DOCS_DIR, exist_ok=True)
out = os.path.join(DOCS_DIR, "quality_rules.pdf")
pdf.output(out)
print(f"PDF generated: {out}")
