import streamlit as st
import pandas as pd
import re
import io
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Costing App", layout="wide")

st.title("📊 Costing Calculator")

# ===============================
# INPUT ZONE
# ===============================
st.subheader("📂 Upload / Paste Quotation")

uploaded_file = st.file_uploader("Upload PDF / Excel / Image", type=["pdf","xlsx","jpg","png"])

# ⭐ เพิ่มตรงนี้ → Paste image
pasted_image = st.clipboard_image()

rate = st.number_input("Exchange Rate", value=33.0)
freight = st.number_input("Freight USD", value=0.0)
tax = st.number_input("Tax %", value=0.0)
containers = st.number_input("Containers", value=0)
clearing_per = st.number_input("Clearing / Container", value=40000.0)

# ===============================
# OCR FUNCTION
# ===============================
def extract_items_from_text(text):
    rows = []
    for line in text.split("\n"):
        match = re.search(r"^(.*?)\s+([\d,]+\.\d+)$", line.strip())
        if match:
            item = match.group(1)
            amount = float(match.group(2).replace(",",""))
            rows.append([item,1,amount])
    return pd.DataFrame(rows, columns=["Item","Qty","Unit Price"])

df = pd.DataFrame(columns=["Item","Qty","Unit Price"])

# ===============================
# FILE PROCESSING
# ===============================
if uploaded_file:

    # PDF
    if uploaded_file.name.endswith(".pdf"):
        images = convert_from_bytes(uploaded_file.read())
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        df = extract_items_from_text(text)

    # Excel
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)

    # Image upload
    elif uploaded_file.name.endswith(("jpg","png")):
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)
        df = extract_items_from_text(text)

# ===============================
# PASTE IMAGE PROCESSING
# ===============================
# ===============================
# TABLE EDIT
# ===============================
st.subheader("Items")
df = st.data_editor(df, num_rows="dynamic")

# ===============================
# CALCULATION
# ===============================
if st.button("Calculate"):

    df["FOB"] = df["Qty"] * df["Unit Price"]
    total_fob = df["FOB"].sum()

    freight_thb = freight * rate
    tax_thb = ((total_fob + freight) * tax / 100) * rate
    clearing_thb = containers * clearing_per
    total_extra = freight_thb + tax_thb + clearing_thb

    result = []

    for _, row in df.iterrows():
        ratio = row["FOB"] / total_fob if total_fob else 0
        allocated = total_extra * ratio
        total_cost = (row["FOB"] * rate) + allocated
        cost_unit = total_cost / row["Qty"] if row["Qty"] else 0

        result.append({
            "Item": row["Item"],
            "Cost/Unit": round(cost_unit,2),
            "Total Price": round(total_cost,2)
        })

    result_df = pd.DataFrame(result)

    st.subheader("Result")
    st.dataframe(result_df)

    # Export Excel
    excel_buffer = io.BytesIO()
    result_df.to_excel(excel_buffer, index=False)

    st.download_button(
        "⬇ Download Excel",
        excel_buffer.getvalue(),
        file_name="costing.xlsx"
    )

    # Export PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer)
    y = 800
    c.drawString(50,y,"Costing Result")
    y -= 30
    for _, r in result_df.iterrows():
        c.drawString(50,y,f"{r['Item']} - {r['Cost/Unit']}")
        y -= 20
    c.save()

    st.download_button(
        "⬇ Download PDF",
        pdf_buffer.getvalue(),
        file_name="costing.pdf"
    )
