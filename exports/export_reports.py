"""
Adventure Works — Snowflake Report Exporter
Generates Excel workbook + PDF summary from Gold layer data.

Requirements:
    pip install snowflake-connector-python pandas openpyxl xlsxwriter reportlab
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import snowflake.connector

# ReportLab for PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, HRFlowable
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.snowflake_config import SNOWFLAKE_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DATE = datetime.now().strftime("%Y-%m-%d")
EXCEL_PATH  = OUTPUT_DIR / f"adventure_works_report_{REPORT_DATE}.xlsx"
PDF_PATH    = OUTPUT_DIR / f"adventure_works_summary_{REPORT_DATE}.pdf"

DB = "ADVENTURE_WORKS_DB"
GOLD = f"{DB}.GOLD"


# ── Snowflake Query Runner ─────────────────────────────────────────────────────

def get_connection():
    cfg = dict(SNOWFLAKE_CONFIG)
    cfg["schema"] = "GOLD"
    return snowflake.connector.connect(**cfg)


def query_to_df(conn, sql: str, title: str = "") -> pd.DataFrame:
    log.info("Fetching: %s", title or sql[:60])
    cur = conn.cursor()
    cur.execute(sql)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=cols)


# ── Query Definitions ──────────────────────────────────────────────────────────

QUERIES = {
    "Sales_By_Year": f"""
        SELECT d.YEAR,
               COUNT(DISTINCT f.ORDER_NUMBER)           AS TOTAL_ORDERS,
               SUM(f.ORDER_QUANTITY)                    AS TOTAL_UNITS,
               ROUND(SUM(f.GROSS_REVENUE),  2)          AS TOTAL_REVENUE,
               ROUND(SUM(f.GROSS_PROFIT),   2)          AS TOTAL_PROFIT,
               ROUND(AVG(f.MARGIN_PCT),     2)          AS AVG_MARGIN_PCT
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
        GROUP BY d.YEAR ORDER BY d.YEAR
    """,

    "Monthly_Revenue_Trend": f"""
        SELECT d.YEAR, d.MONTH_NUM, d.MONTH_NAME,
               ROUND(SUM(f.GROSS_REVENUE), 2)  AS MONTHLY_REVENUE,
               ROUND(SUM(f.GROSS_PROFIT),  2)  AS MONTHLY_PROFIT
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
        GROUP BY 1,2,3 ORDER BY 1,2
    """,

    "Revenue_By_Category": f"""
        SELECT p.CATEGORY_NAME, p.SUBCATEGORY_NAME,
               SUM(f.ORDER_QUANTITY)           AS UNITS_SOLD,
               ROUND(SUM(f.GROSS_REVENUE), 2)  AS TOTAL_REVENUE,
               ROUND(SUM(f.GROSS_PROFIT),  2)  AS TOTAL_PROFIT,
               ROUND(AVG(f.MARGIN_PCT),    2)  AS AVG_MARGIN_PCT
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY
        GROUP BY 1,2 ORDER BY TOTAL_REVENUE DESC
    """,

    "Top_20_Products": f"""
        SELECT p.PRODUCT_NAME, p.CATEGORY_NAME, p.PRICE_TIER,
               SUM(f.ORDER_QUANTITY)           AS UNITS_SOLD,
               ROUND(SUM(f.GROSS_REVENUE), 2)  AS TOTAL_REVENUE
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY
        GROUP BY 1,2,3 ORDER BY UNITS_SOLD DESC LIMIT 20
    """,

    "Revenue_By_Territory": f"""
        SELECT t.CONTINENT, t.COUNTRY, t.REGION,
               COUNT(DISTINCT f.ORDER_NUMBER)  AS TOTAL_ORDERS,
               ROUND(SUM(f.GROSS_REVENUE), 2)  AS TOTAL_REVENUE,
               ROUND(SUM(f.GROSS_PROFIT),  2)  AS TOTAL_PROFIT
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_TERRITORY t ON f.TERRITORY_KEY = t.TERRITORY_KEY
        GROUP BY 1,2,3 ORDER BY TOTAL_REVENUE DESC
    """,

    "Customer_Segmentation": f"""
        SELECT c.INCOME_BAND, c.OCCUPATION, c.GENDER,
               COUNT(DISTINCT c.CUSTOMER_KEY)              AS CUSTOMERS,
               ROUND(SUM(f.GROSS_REVENUE), 2)              AS TOTAL_REVENUE,
               ROUND(SUM(f.GROSS_REVENUE)/COUNT(DISTINCT c.CUSTOMER_KEY), 2)
                                                           AS REVENUE_PER_CUSTOMER
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
        GROUP BY 1,2,3 ORDER BY REVENUE_PER_CUSTOMER DESC
    """,

    "Top_20_Customers_CLV": f"""
        SELECT c.CUSTOMER_KEY, c.FULL_NAME, c.OCCUPATION, c.INCOME_BAND,
               COUNT(DISTINCT f.ORDER_NUMBER)   AS TOTAL_ORDERS,
               ROUND(SUM(f.GROSS_REVENUE), 2)   AS LIFETIME_REVENUE
        FROM {GOLD}.FACT_SALES f
        JOIN {GOLD}.DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
        GROUP BY 1,2,3,4 ORDER BY LIFETIME_REVENUE DESC LIMIT 20
    """,

    "Return_Analysis": f"""
        SELECT p.PRODUCT_NAME, p.CATEGORY_NAME,
               SUM(r.RETURN_QUANTITY)                AS UNITS_RETURNED,
               ROUND(SUM(r.RETURN_REVENUE_IMPACT), 2) AS REVENUE_IMPACT
        FROM {GOLD}.FACT_RETURNS r
        JOIN {GOLD}.DIM_PRODUCT p ON r.PRODUCT_KEY = p.PRODUCT_KEY
        GROUP BY 1,2 ORDER BY UNITS_RETURNED DESC LIMIT 20
    """,
}


# ── Excel Export ───────────────────────────────────────────────────────────────

HEADER_COLOR = "#1F3864"
ALT_ROW_COLOR = "#EBF3FB"

def export_excel(dataframes: dict):
    log.info("Writing Excel: %s", EXCEL_PATH)
    with pd.ExcelWriter(EXCEL_PATH, engine="xlsxwriter") as writer:
        wb = writer.book
        hdr_fmt = wb.add_format({
            "bold": True, "font_color": "#FFFFFF",
            "bg_color": HEADER_COLOR, "border": 1,
            "align": "center", "valign": "vcenter"
        })
        num_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1})
        int_fmt = wb.add_format({"num_format": "#,##0",    "border": 1})
        alt_fmt = wb.add_format({"bg_color": ALT_ROW_COLOR, "border": 1})

        # Cover sheet
        cover = wb.add_worksheet("Cover")
        cover.write("B2", "Adventure Works — Snowflake Capstone Report",
                    wb.add_format({"bold": True, "font_size": 18}))
        cover.write("B3", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    wb.add_format({"italic": True, "font_size": 12}))
        cover.write("B4", f"Snowflake Account: uq57089.ap-southeast-7.aws",
                    wb.add_format({"font_size": 11}))
        cover.write("B5", f"Database: ADVENTURE_WORKS_DB",
                    wb.add_format({"font_size": 11}))
        cover.set_column("A:A", 3)
        cover.set_column("B:B", 60)

        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False, startrow=1)
            ws = writer.sheets[sheet_name[:31]]

            for col_idx, col_name in enumerate(df.columns):
                ws.write(0, col_idx, col_name, hdr_fmt)
                col_width = max(len(col_name) + 2, 12)
                ws.set_column(col_idx, col_idx, col_width)

            for row_idx in range(len(df)):
                for col_idx, val in enumerate(df.iloc[row_idx]):
                    fmt = alt_fmt if row_idx % 2 == 0 else None
                    if isinstance(val, float):
                        ws.write(row_idx + 1, col_idx, val, num_fmt)
                    elif isinstance(val, int):
                        ws.write(row_idx + 1, col_idx, val, int_fmt)
                    elif fmt:
                        ws.write(row_idx + 1, col_idx, val, fmt)

            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
            ws.freeze_panes(1, 0)

    log.info("Excel saved: %s", EXCEL_PATH)


# ── PDF Export ─────────────────────────────────────────────────────────────────

def _df_to_pdf_table(df: pd.DataFrame) -> Table:
    data = [list(df.columns)]
    for _, row in df.iterrows():
        data.append([str(v) for v in row])

    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1F3864")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#EBF3FB"), colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP",     (0, 0), (-1, -1), True),
    ]))
    return tbl


def export_pdf(dataframes: dict):
    log.info("Writing PDF: %s", PDF_PATH)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"],
                                 fontSize=18, spaceAfter=6)
    h1_style = ParagraphStyle("H1", parent=styles["Heading1"],
                               fontSize=13, spaceAfter=4)

    story = []
    story.append(Paragraph("Adventure Works — Snowflake Capstone Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Account: uq57089.ap-southeast-7.aws  |  DB: ADVENTURE_WORKS_DB",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F3864")))
    story.append(Spacer(1, 0.5*cm))

    for name, df in dataframes.items():
        story.append(Paragraph(name.replace("_", " "), h1_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(_df_to_pdf_table(df))
        story.append(Spacer(1, 0.5*cm))
        story.append(PageBreak())

    doc.build(story)
    log.info("PDF saved: %s", PDF_PATH)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log.info("=== ADVENTURE WORKS REPORT EXPORT STARTED ===")
    conn = get_connection()
    dataframes = {}
    for name, sql in QUERIES.items():
        try:
            df = query_to_df(conn, sql, title=name)
            dataframes[name] = df
            log.info("  %-35s  %d rows", name, len(df))
        except Exception as exc:
            log.error("  FAILED %s: %s", name, exc)
    conn.close()

    if not dataframes:
        log.error("No data retrieved — check Snowflake connection and Gold layer load.")
        sys.exit(1)

    export_excel(dataframes)
    export_pdf(dataframes)

    log.info("=== EXPORT COMPLETE ===")
    log.info("Excel : %s", EXCEL_PATH)
    log.info("PDF   : %s", PDF_PATH)


if __name__ == "__main__":
    main()
