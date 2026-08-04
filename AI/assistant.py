"""AI Data Governance Assistant.

After each ETL execution, this module:
  1. Reads the issues detected in Fact_Accuracy (DWH) during the last run.
  2. Asks the local Ollama LLM to explain each error, its root cause,
     business impact, corrective actions and severity.
  3. Composes and sends a professional email notification (SMTP Gmail).

No new table is created: everything is read from Fact_Accuracy.
"""

import logging
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ollama_client import OllamaClient
from email_notifier import send_email, is_email_configured

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.2:3b"
MAX_ISSUES_IN_EMAIL = 8  # detailed issues included in the email

# Severity priority (higher = more critical), used to order errors in the email
SEVERITY_RANK = {"High": 3, "Medium": 2, "Low": 1}
SEVERITY_COLORS = {
    "High": "#dc2626",
    "Medium": "#d97706",
    "Low": "#16a34a",
}


def severity_rank(issue):
    """Return sort key (rank desc, then detection date desc, then key asc)."""
    sev = str(issue.get("Severity") or "Low").strip()
    rank = -SEVERITY_RANK.get(sev, 1)
    detection = issue.get("Date_Detection")
    detection_ts = detection.timestamp() if hasattr(detection, "timestamp") else 0
    return (rank, -detection_ts, -int(issue.get("Accuracy_Key") or 0))


def sort_and_group_issues(issues):
    """Sort issues by severity priority, then group by severity.

    Returns an ordered list of (severity, [issues_in_group]) tuples,
    from most critical to least critical (High, Medium, Low).
    """
    ordered = sorted(issues, key=severity_rank)
    groups = {}
    for issue in ordered:
        sev = str(issue.get("Severity") or "Low").strip()
        # Map unknown severities into known buckets
        key = sev if sev in SEVERITY_RANK else "High"
        groups.setdefault(key, []).append(issue)
    order = sorted(groups.keys(), key=lambda k: -SEVERITY_RANK.get(k, 0))
    return [(sev, groups[sev]) for sev in order]


def get_recent_issues(dwh_conn, since=None, limit=20):
    """Return active issues from Fact_Accuracy, newest first.

    If `since` is provided (datetime), only issues whose Date_Detection
    is >= since are returned (i.e. issues detected by the last run).
    """
    sql = (
        "SELECT TOP (?) f.Accuracy_Key, f.Table_Name, f.Column_Name, "
        "       f.Valeur_Erreur, f.Valeur_Attendue, f.Error_Message, "
        "       f.Severity, f.Date_Detection, "
        "       COALESCE(a.Nom_Agence, 'Inconnue') "
        "FROM Fact_Accuracy f "
        "LEFT JOIN Dim_Agence a ON f.Agence_Key = a.Agence_Key "
        "WHERE f.Solved = 0"
    )
    params = [limit]
    if since is not None:
        sql += " AND f.Date_Detection >= ?"
        params.append(since)
    sql += " ORDER BY f.Date_Detection DESC"

    cursor = dwh_conn.cursor()
    cursor.execute(sql, *params)
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def count_active_issues(dwh_conn):
    cursor = dwh_conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM Fact_Accuracy WHERE Solved = 0"
    )
    return cursor.fetchone()[0]


DOMAIN_LABELS = {
    "Client": "client relationship, KYC compliance and customer data",
    "Compte": "account management, balance reporting and regulatory reporting",
    "Transaction_Bancaire": "transaction processing, anti-fraud controls and financial statements",
    "Credit": "credit risk assessment, provisioning and loan portfolio quality",
}


def build_analysis_prompt(issue):
    domain = str(issue.get("Table_Name") or "Données")
    domain_context = DOMAIN_LABELS.get(domain, "core banking operations")
    return f"""You are the Business Impact Analyst of "CoreBanking", a Tunisian
commercial bank. A data quality (accuracy) issue was detected by our
automated data governance pipeline and recorded in the DWH.

The affected business process is: {domain_context}.
The affected entity belongs to agency: {issue.get('Nom_Agence', 'N/A')}.

ISSUE DETAILS:
- Error record ID: {issue['Accuracy_Key']}
- Source table: {issue['Table_Name']}
- Column: {issue['Column_Name']}
- Detected value: '{issue['Valeur_Erreur']}'
- Expected value: '{issue['Valeur_Attendue']}'
- Error message: {issue['Error_Message']}
- Current severity: {issue['Severity']}

Produce a professional BUSINESS IMPACT analysis with EXACTLY these 7 fields,
one field per line (values may span multiple lines, keep each under 60 words):

EXPLANATION: <what the error means, in plain business language>
ROOT_CAUSE: <most likely operational root cause>
BUSINESS_IMPACT: <tangible impact on revenue, operational risk, customers or
  regulatory compliance (BCT, Basel, GDPR), quantified when possible>
FINANCIAL_IMPACT: <potential financial consequence or exposure estimate>
CORRECTIVE_ACTION: <concrete steps for the operations team to fix the data>
RISK_LEVEL: <Low | Medium | High>
PRIORITY: <P1 | P2 | P3> (P1 = fix immediately, P3 = fix during routine maintenance)

IMPORTANT: always write all 7 fields, and ALWAYS end your response with the
PRIORITY line as the very last line. Do not stop before PRIORITY.

Be concise, business-oriented, decision-ready."""


def analyze_issue_with_ai(ollama, model, issue):
    """Ask Ollama to analyze one issue; return the raw analysis text."""
    prompt = build_analysis_prompt(issue)
    try:
        return ollama.chat(
            model,
            [
                {
                    "role": "system",
                    "content": "You are a precise business impact analyst at a "
                    "bank. Answer only with the requested fields.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
    except Exception as e:
        logger.error(f"Erreur IA pour l'issue {issue['Accuracy_Key']}: {e}")
        return (
            "EXPLANATION: (analyse IA indisponible)\n"
            f"ROOT_CAUSE: erreur de connexion au modèle local: {e}\n"
            "BUSINESS_IMPACT: à évaluer manuellement\n"
            "FINANCIAL_IMPACT: à évaluer\n"
            f"RISK_LEVEL: {issue['Severity']}\n"
            "PRIORITY: P2\n"
            "CORRECTIVE_ACTION: vérifier la donnée source et corriger\n"
        )


ANALYSIS_FIELDS = (
    "EXPLANATION",
    "ROOT_CAUSE",
    "BUSINESS_IMPACT",
    "FINANCIAL_IMPACT",
    "RISK_LEVEL",
    "PRIORITY",
    "CORRECTIVE_ACTION",
)


def parse_analysis(text):
    """Robustly parse the AI analysis into a dict of the 5 fields.

    Handles both 'FIELD: value' on one line and 'FIELD:' followed by
    a multi-line value (which the LLM often produces).
    """
    parsed = {}
    current_key = None
    current_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = None
        for field in ANALYSIS_FIELDS:
            if line.upper().startswith(field):
                matched = field
                break
        if matched:
            if current_key:
                parsed[current_key] = " ".join(current_lines).strip()
            rest = line[len(matched):].lstrip(":").strip()
            current_key = matched
            current_lines = [rest] if rest else []
        elif current_key:
            current_lines.append(line)
    if current_key:
        parsed[current_key] = " ".join(current_lines).strip()
    return parsed


def build_email_body(issues, analyses, execution_status, dwh_name="CoreBanking_DW"):
    """Compose a professional, severity-prioritized HTML + text email body.

    Issues are sorted by severity (High -> Medium -> Low) and
    rendered in dedicated sections per severity level.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Reference query for each error record in the DWH
    link = ("SELECT * FROM Fact_Accuracy WHERE Accuracy_Key = <ID>")

    # Associate each issue with its analysis, then sort by severity priority
    paired = sorted(
        list(zip(issues, analyses)),
        key=lambda pair: severity_rank(pair[0]),
    )
    ordered_issues = [p[0] for p in paired]
    ordered_analyses = [p[1] for p in paired]

    # ---- Severity counts (for KPI cards) ----
    sev_counts = {}
    for i in ordered_issues:
        sev = str(i.get("Severity") or "Low").strip()
        sev = sev if sev in SEVERITY_RANK else "High"
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    # ---- Text rows (prioritized, with full 7-field analysis) ----
    rows_txt = ""
    for issue, analysis in paired:
        parsed = parse_analysis(analysis)
        rows_txt += (
            f"\n  [#{issue['Accuracy_Key']}] [{issue['Severity']}] "
            f"{issue['Table_Name']}.{issue['Column_Name']}\n"
            f"    Valeur: {issue['Valeur_Erreur']} | Attendu: {issue['Valeur_Attendue']}\n"
            f"    Message: {issue['Error_Message']} | Agence: {issue.get('Nom_Agence', 'N/A')}\n"
            f"    Explication: {parsed.get('EXPLANATION', 'N/A')}\n"
            f"    Cause racine: {parsed.get('ROOT_CAUSE', 'N/A')}\n"
            f"    Impact metier: {parsed.get('BUSINESS_IMPACT', 'N/A')}\n"
            f"    Impact financier: {parsed.get('FINANCIAL_IMPACT', 'N/A')}\n"
            f"    Risque: {parsed.get('RISK_LEVEL', issue['Severity'])} | "
            f"Priorite: {parsed.get('PRIORITY', 'P2')}\n"
            f"    Action corrective: {parsed.get('CORRECTIVE_ACTION', 'N/A')}\n"
        )

    # ---- HTML: summary table by severity (prioritized) ----
    kpi_cells = ""
    for sev in sorted(SEVERITY_RANK, key=lambda k: -SEVERITY_RANK[k]):
        color = SEVERITY_COLORS[sev]
        kpi_cells += f"""
        <td style="width:21%;background:#ffffff;border:1px solid {color}33;border-top:4px solid {color};
                   border-radius:12px;padding:14px;text-align:center;box-shadow:0 2px 6px rgba(15,23,42,.04);">
          <div style="font-size:11px;color:{color};font-weight:700;letter-spacing:.8px;">{sev.upper()}</div>
          <div style="font-size:28px;font-weight:800;color:#1e293b;line-height:1.2;">{sev_counts.get(sev, 0)}</div>
          <div style="font-size:10.5px;color:#94a3b8;">erreurs</div>
        </td>"""

    # ---- HTML: issue table rows (prioritized, with severity badge) ----
    rows_html = ""
    for i, issue in enumerate(ordered_issues):
        sev = str(issue.get("Severity") or "Low").strip()
        sev = sev if sev in SEVERITY_RANK else "High"
        color = SEVERITY_COLORS.get(sev, "#64748b")
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        rows_html += f"""
        <tr style="background:{bg};border-bottom:1px solid #eef2f7;">
          <td style="padding:9px 10px;color:#64748b;">#{issue['Accuracy_Key']}</td>
          <td style="padding:9px 10px;font-weight:600;color:#0f172a;">{issue['Table_Name']}</td>
          <td style="padding:9px 10px;color:#334155;">{issue['Column_Name']}</td>
          <td style="padding:9px 10px;color:#dc2626;font-family:Consolas,monospace;">{issue['Valeur_Erreur']}</td>
          <td style="padding:9px 10px;color:#16a34a;font-family:Consolas,monospace;">{issue['Valeur_Attendue']}</td>
          <td style="padding:9px 10px;text-align:center;">
            <span style="background:{color}1a;color:{color};padding:3px 10px;border-radius:999px;
                  font-weight:700;font-size:10.5px;letter-spacing:.5px;">
              {sev.upper()}</span>
          </td>
        </tr>"""

    # ---- HTML: AI analysis grouped by severity ----
    groups = sort_and_group_issues(ordered_issues)
    analyses_html = ""
    for sev, group in groups:
        color = SEVERITY_COLORS.get(sev, "#0f172a")
        analyses_html += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    background:{color}18;border-left:5px solid {color};border-radius:8px 8px 0 0;
                    padding:10px 14px;margin-top:16px;">
          <span style="font-size:12px;font-weight:800;color:{color};letter-spacing:.8px;">
            PRIORITE {SEVERITY_RANK.get(sev, 0)} - {sev.upper()}</span>
          <span style="font-size:11px;color:#475569;font-weight:600;">
            {len(group)} erreur(s)</span>
        </div>
        <div style="background:#ffffff;border:1px solid {color}2e;border-top:none;border-radius:0 0 8px 8px;
                    padding:10px 14px;">"""
        for issue in group:
            pair = next(p for p in paired if p[0]["Accuracy_Key"] == issue["Accuracy_Key"])
            analysis = pair[1]
            parsed = parse_analysis(analysis)
            risk = str(parsed.get("RISK_LEVEL") or issue.get("Severity") or "High")
            risk = risk if risk in SEVERITY_RANK else ("High" if risk not in ("Low", "Medium") else risk)
            risk_color = SEVERITY_COLORS.get(risk, "#0f172a")
            prio = str(parsed.get("PRIORITY") or "P2").upper()
            prio_color = {"P1": "#dc2626", "P2": "#d97706", "P3": "#16a34a"}.get(prio, "#64748b")
            badge_p = {"P1": "CRITIQUE", "P2": "IMPORTANT", "P3": "STANDARD"}.get(prio, prio)
            analyses_html += f"""
            <div style="border:1px solid #eaeef5;border-radius:8px;padding:13px 14px;margin:8px 0;background:#fbfdff;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-weight:700;color:#0f172a;font-size:13px;">
                  #{issue['Accuracy_Key']} <span style="color:#64748b;font-weight:400;">
                  &mdash; {issue['Table_Name']}.{issue['Column_Name']}</span></span>
                <span style="white-space:nowrap;">
                  <span style="display:inline-block;background:{risk_color}1a;color:{risk_color};
                        padding:3px 9px;border-radius:999px;font-weight:700;font-size:10px;
                        letter-spacing:.4px;margin-right:4px;">RISQUE {risk.upper()}</span>
                  <span style="display:inline-block;background:{prio_color}1a;color:{prio_color};
                        padding:3px 9px;border-radius:999px;font-weight:700;font-size:10px;
                        letter-spacing:.4px;">{badge_p}</span>
                </span>
              </div>
              <table style="width:100%;border-collapse:collapse;font-size:11.5px;">
                <tr>
                  <td style="width:130px;padding:3px 8px 3px 0;color:#64748b;font-weight:600;vertical-align:top;">
                    Explication</td>
                  <td style="padding:3px 0;color:#334155;vertical-align:top;">{parsed.get('EXPLANATION','N/A')}</td>
                </tr>
                <tr>
                  <td style="padding:3px 8px 3px 0;color:#64748b;font-weight:600;vertical-align:top;">
                    Cause racine</td>
                  <td style="padding:3px 0;color:#334155;vertical-align:top;">{parsed.get('ROOT_CAUSE','N/A')}</td>
                </tr>
                <tr>
                  <td style="padding:3px 8px 3px 0;color:{color};font-weight:700;vertical-align:top;">
                    Impact métier</td>
                  <td style="padding:3px 0;color:#0f172a;vertical-align:top;">{parsed.get('BUSINESS_IMPACT','N/A')}</td>
                </tr>
                <tr>
                  <td style="padding:3px 8px 3px 0;color:#b45309;font-weight:700;vertical-align:top;">
                    Impact financier</td>
                  <td style="padding:3px 0;color:#b45309;vertical-align:top;">{parsed.get('FINANCIAL_IMPACT','N/A')}</td>
                </tr>
                <tr>
                  <td style="padding:3px 8px 3px 0;color:#0f172a;font-weight:600;vertical-align:top;border-top:1px dashed #eef2f7;">
                    Action corrective</td>
                  <td style="padding:3px 0;color:#334155;vertical-align:top;border-top:1px dashed #eef2f7;">
                    {parsed.get('CORRECTIVE_ACTION','N/A')}</td>
                </tr>
              </table>
            </div>"""
        analyses_html += "</div>"

    body_text = f"""
====================================================================
 AI DATA GOVERNANCE ASSISTANT - ALERTE QUALITE DES DONNEES
====================================================================
Execution ETL : {execution_status}
Date          : {now}
Base          : {dwh_name}
Issues actives: {len(issues)} détectées lors de cette exécution
--------------------------------------------------------------------
Récapitulatif par sévérité :
{chr(10).join(f"  - {sev}: {sev_counts.get(sev, 0)}" for sev in sorted(SEVERITY_RANK, key=lambda k: -SEVERITY_RANK[k]))}
--------------------------------------------------------------------

DETAIL DES ERREURS (triées par priorité : High > Medium > Low):
{rows_txt}

POUR CONSULTER CHAQUE ENREGISTREMENT DANS LE DWH:
  USE {dwh_name};
  {link} -- (remplacer Accuracy_Key par l'id souhaité)
  -- ou simplement:
  SELECT * FROM Fact_Accuracy WHERE Solved = 0;

Ce message a été généré automatiquement après l'exécution du pipeline ETL
par le module AI Data Governance Assistant (Ollama local).
====================================================================
"""

    body_html = f"""
<html><body style="margin:0;padding:24px;background:#eef2f7;font-family:Segoe UI,Arial,sans-serif;">
<div style="max-width:780px;margin:auto;background:#ffffff;border-radius:14px;overflow:hidden;
            border:1px solid #dbe3ee;box-shadow:0 6px 18px rgba(15,23,42,.08);">

  <!-- ============ HEADER ============ -->
  <div style="background:linear-gradient(135deg,#0f172a 0%,#16324f 55%,#1d4ed8 100%);
              padding:26px 30px;color:#ffffff;position:relative;">
    <div style="font-size:10.5px;letter-spacing:2.5px;color:#93c5fd;text-transform:uppercase;margin-bottom:6px;">
      CoreBanking DWH &bull; Data Governance</div>
    <div style="font-size:20px;font-weight:700;">AI Data Governance - Alerte Qualité des Données</div>
    <div style="font-size:12px;color:#cbd5e1;margin-top:6px;">
      Exécution ETL : <span style="color:#4ade80;font-weight:600;">
      {execution_status}</span> &nbsp;&bull;&nbsp; {now} &nbsp;&bull;&nbsp; Base : {dwh_name}</div>
    <div style="position:absolute;top:22px;right:28px;background:rgba(255,255,255,.12);
                border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:6px 14px;
                font-size:11px;font-weight:600;letter-spacing:.5px;">
      OLLAMA AI &bull; LOCAL</div>
  </div>

  <div style="padding:24px 30px;">

    <!-- ============ KPI CARDS ============ -->
    <table style="width:100%;border-collapse:separate;border-spacing:0 0;margin-bottom:6px;">
      <tr>
        <td style="width:34%;background:linear-gradient(180deg,#eef2ff,#e0e7ff);
                   border-radius:12px;padding:16px;text-align:center;">
          <div style="font-size:11px;color:#4f46e5;font-weight:700;letter-spacing:.5px;text-transform:uppercase;">
            Total des issues</div>
          <div style="font-size:30px;font-weight:800;color:#1e1b4b;line-height:1.15;">{len(issues)}</div>
          <div style="font-size:10.5px;color:#6366f1;">actives après ETL</div>
        </td>
        <td style="width:3%;"></td>
        {kpi_cells}
      </tr>
    </table>

    <!-- ============ TABLE ERREURS ============ -->
    <div style="margin-top:22px;">
      <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:2px;">
        Erreurs détectées</div>
      <div style="font-size:11.5px;color:#64748b;margin-bottom:10px;">
        Triées par priorité - extrait de <code style="background:#f1f5f9;padding:1px 5px;border-radius:4px;">Fact_Accuracy</code></div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;
                    border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
        <tr style="background:#0f172a;color:#ffffff;">
          <th style="padding:9px 10px;text-align:left;">ID</th>
          <th style="padding:9px 10px;text-align:left;">Table</th>
          <th style="padding:9px 10px;text-align:left;">Colonne</th>
          <th style="padding:9px 10px;text-align:left;">Valeur détectée</th>
          <th style="padding:9px 10px;text-align:left;">Valeur attendue</th>
          <th style="padding:9px 10px;text-align:center;">Sévérité</th>
        </tr>
        {rows_html}
      </table>
    </div>

    <!-- ============ ANALYSE IA ============ -->
    <div style="margin-top:26px;">
      <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:2px;">
        Analyse IA - Business Impact</div>
      <div style="font-size:11.5px;color:#64748b;margin-bottom:10px;">
        Générée localement par le modèle Ollama pour chaque anomalie</div>
      {analyses_html}
    </div>

    <!-- ============ CONSULTATION DWH ============ -->
    <div style="margin-top:22px;background:#0f172a;border-radius:10px;padding:14px 16px;">
      <div style="font-size:11px;color:#93c5fd;font-weight:700;letter-spacing:.5px;margin-bottom:6px;">
        CONSULTATION DANS LE DWH</div>
      <code style="font-size:11px;color:#e2e8f0;line-height:1.6;">
        USE {dwh_name}; <br>
        SELECT * FROM Fact_Accuracy WHERE Solved = 0; <br>
        <span style="color:#64748b;">-- ou par id : {link}</span>
      </code>
    </div>
  </div>

  <!-- ============ FOOTER ============ -->
  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:14px 30px;
              font-size:11px;color:#64748b;line-height:1.6;">
    Email généré automatiquement par le module <b>AI Data Governance Assistant</b>
    après exécution du pipeline ETL.<br>
    Analyse 100% locale (Ollama) - aucune donnée transmise vers le cloud.
  </div>
</div>
</body></html>
"""
    return body_text, body_html


def run_assistant(dwh_conn, model=DEFAULT_MODEL, since=None, execution_status="SUCCESS"):
    """Main entry point: analyze recent issues and send the email.

    Returns a dict with the notification result. Never raises: failures
    are captured and returned so the ETL pipeline is not blocked.
    """
    result = {
        "status": "success",
        "issues_count": 0,
        "email_sent": False,
        "model": model,
        "error": None,
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        issues = get_recent_issues(dwh_conn, since=since, limit=MAX_ISSUES_IN_EMAIL)
        result["issues_count"] = len(issues)
        if not issues:
            logger.info("Assistant IA : aucune issue active récente, pas d'email.")
            result["status"] = "skipped"
            result["error"] = "no_new_issues"
            return result

        logger.info(f"Assistant IA : {len(issues)} issue(s) à analyser avec {model}...")
        ollama = OllamaClient()
        if not ollama.is_server_running():
            raise RuntimeError(
                "Serveur Ollama inaccessible sur localhost:11434 - démarrez Ollama"
            )
        if model not in ollama.list_models():
            logger.warning(f"Modèle {model} absent - tentative d'analyse quand même.")

        analyses = [analyze_issue_with_ai(ollama, model, i) for i in issues]

        body_text, body_html = build_email_body(issues, analyses, execution_status)
        subject = (
            f"[Data Governance] {len(issues)} issue(s) de qualité détectées - "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        send_email(subject, body_text, body_html)
        result["email_sent"] = True
        logger.info("Assistant IA : email d'alerte envoyé avec succès.")
    except Exception as e:
        logger.error(f"Assistant IA : erreur - {e}")
        result["status"] = "error"
        result["error"] = str(e)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import pyodbc

    print("=== AI Data Governance Assistant - Test manuel ===")
    print("Config SMTP chargée :", is_email_configured())

    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;"
        "DATABASE=CoreBanking_DW;Trusted_Connection=yes;",
        autocommit=True,
    )
    res = run_assistant(conn, model=DEFAULT_MODEL)
    print("\nRésultat :", res)
    conn.close()
