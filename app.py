import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

st.set_page_config(page_title="Billing & Estimate Studio", layout="wide")

# --- 🏢 HARDCODED BUSINESS CONFIGURATION ---
BUSINESS_CONFIG = {
    "company_name": "SENSIBLE HIFI",
    "address_line1": "24 Don Rose Blvd",
    "address_line2": "Mount Albert, ON, Canada",
    "postal_code": "L0G 1M0"
}

# --- 🔒 PERMANENT EMAIL CONFIGURATION ---
FALLBACK_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "allen@sensiblehifi.com", 
    "sender_password": "keggjjfwfenvugid"  # Replace with your 16-character App Password
}

try:
    if hasattr(st, "secrets") and len(st.secrets) > 0:
        SMTP_SERVER_DEFAULT = st.secrets.get("SMTP_SERVER", FALLBACK_CONFIG["smtp_server"])
        SMTP_PORT_DEFAULT = st.secrets.get("SMTP_PORT", FALLBACK_CONFIG["smtp_port"])
        SENDER_EMAIL_DEFAULT = st.secrets.get("SENDER_EMAIL", FALLBACK_CONFIG["sender_email"])
        SENDER_PASSWORD_DEFAULT = st.secrets.get("SENDER_PASSWORD", FALLBACK_CONFIG["sender_password"])
    else:
        raise AttributeError
except:
    SMTP_SERVER_DEFAULT = FALLBACK_CONFIG["smtp_server"]
    SMTP_PORT_DEFAULT = FALLBACK_CONFIG["smtp_port"]
    SENDER_EMAIL_DEFAULT = FALLBACK_CONFIG["sender_email"]
    SENDER_PASSWORD_DEFAULT = FALLBACK_CONFIG["sender_password"]


# --- MASTER SESSION STATE PERSISTENCE INITIALIZATION ---
if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = {
        "Product": [], "Description": [], "Quantity": [], "Item Amount": [],
        "Discount Type": [], "Discount Given": [], "Line Discount": [], "Subtotal": [],
        "Sales Tax": []
    }
if "doc_type" not in st.session_state:
    st.session_state.doc_type = "Invoice"
if "doc_id" not in st.session_state:
    st.session_state.doc_id = "1001"
if "doc_date" not in st.session_state:
    st.session_state.doc_date = datetime.today().date()
if "terms" not in st.session_state:
    st.session_state.terms = "Due on Receipt"
if "due_date" not in st.session_state:
    st.session_state.due_date = datetime.date.today()
if "cust_name" not in st.session_state:
    st.session_state.cust_name = ""
if "cust_email" not in st.session_state:
    st.session_state.cust_email = ""
if "bin_number" not in st.session_state:
    st.session_state.bin_number = ""
if "tax_rate" not in st.session_state:
    st.session_state.tax_rate = 13.0
if "currency" not in st.session_state:
    st.session_state.currency = "$"

st.title("💼 Invoice & Estimate Studio")
st.caption(f"Engineered for {BUSINESS_CONFIG['company_name']} | Advanced Storage & On-the-Fly Database Sync")

# --- DYNAMIC LAYOUT PRE-CHECK ---
has_any_discount = False
if "invoice_data" in st.session_state and isinstance(st.session_state.invoice_data, dict) and "Line Discount" in st.session_state.invoice_data:
    if len(st.session_state.invoice_data["Line Discount"]) > 0:
        has_any_discount = sum(st.session_state.invoice_data["Line Discount"]) > 0

# --- PERSISTENT DATABASE & APP SETTINGS FILE UTILITIES ---
CUST_FILE_PATH = "qb_customers.csv"
PROD_FILE_PATH = "qb_products.csv"
DB_FILE_PATH = "saved_quotes_db.json"
SETTINGS_FILE_PATH = "app_settings.json"

def load_document_db():
    if os.path.exists(DB_FILE_PATH):
        try:
            with open(DB_FILE_PATH, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_document_db(data):
    with open(DB_FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)

def load_app_settings():
    defaults = {
        "theme_selection": "Deep Corporate Navy",
        "custom_color": "#3182CE",
        "graphic_style": "Modern Minimalist Lines",
        "show_total_background": True,
        "table_spacer_val": 20,
        "cell_padding_val": 6,
        "details_width": -1  # Flag to use dynamic contextual width if never saved
    }
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, "r") as f:
                defaults.update(json.load(f))
        except:
            pass
    return defaults

app_settings = load_app_settings()

def save_app_settings():
    settings = {
        "theme_selection": st.session_state.theme_pref,
        "custom_color": st.session_state.get("custom_color_pref", app_settings["custom_color"]),
        "graphic_style": st.session_state.graphic_pref,
        "show_total_background": st.session_state.total_bg_pref,
        "table_spacer_val": st.session_state.spacer_pref,
        "cell_padding_val": st.session_state.padding_pref,
        "details_width": st.session_state.width_pref
    }
    with open(SETTINGS_FILE_PATH, "w") as f:
        json.dump(settings, f, indent=4)


# --- 🔌 QUICKBOOKS DATA INTEGRATIONS & DIRECTORIES ---
st.sidebar.header("🔌 QuickBooks Integrations")

# 1. READ CUSTOMERS FROM LOCAL DB
customer_dict = {}
if os.path.exists(CUST_FILE_PATH):
    try:
        df_cust = pd.read_csv(CUST_FILE_PATH)
        for _, row in df_cust.iterrows():
            if pd.notna(row.get("Name")):
                customer_dict[str(row["Name"]).strip()] = str(row["Email"]).strip() if pd.notna(row.get("Email")) else ""
    except:
        pass

uploaded_customers = st.sidebar.file_uploader("📂 Upload/Sync QB Customer List (CSV)", type=["csv"])
if uploaded_customers:
    try:
        df_cust_new = pd.read_csv(uploaded_customers)
        df_cust_new.columns = df_cust_new.columns.str.strip()
        name_col = next((c for c in ["Customer", "Full Name", "Name", "Company"] if c in df_cust_new.columns), df_cust_new.columns[0])
        email_col = next((c for c in ["Email", "E-mail", "E-mail Address", "Main Email"] if c in df_cust_new.columns), None)
        clean_cust = pd.DataFrame({"Name": df_cust_new[name_col], "Email": df_cust_new[email_col] if email_col else ""})
        clean_cust.to_csv(CUST_FILE_PATH, index=False)
        st.sidebar.success("Saved customers permanently!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error processing upload: {e}")

# ADD CUSTOMER ON THE FLY
with st.sidebar.expander("👤 ➕ Add New Customer on the Fly"):
    with st.form("add_customer_form", clear_on_submit=True):
        new_cust_name = st.text_input("Customer Name")
        new_cust_email = st.text_input("Customer Email")
        submit_cust = st.form_submit_button("💾 Save Customer to DB")
        if submit_cust:
            if new_cust_name.strip():
                df_c = pd.read_csv(CUST_FILE_PATH) if os.path.exists(CUST_FILE_PATH) else pd.DataFrame(columns=["Name", "Email"])
                df_c = df_c[df_c["Name"].astype(str).str.strip() != new_cust_name.strip()]
                new_row = pd.DataFrame([{"Name": new_cust_name.strip(), "Email": new_cust_email.strip()}])
                df_c = pd.concat([df_c, new_row], ignore_index=True)
                df_c.to_csv(CUST_FILE_PATH, index=False)
                st.toast(f"Customer '{new_cust_name}' appended to database!", icon="👤")
                st.rerun()
            else:
                st.sidebar.error("Customer name cannot be blank.")

if customer_dict:
    st.sidebar.info(f"🎯 Loaded {len(customer_dict)} customers from directory.")


# 2. READ PRODUCTS FROM LOCAL DB
product_dict = {}
if os.path.exists(PROD_FILE_PATH):
    try:
        df_prod = pd.read_csv(PROD_FILE_PATH)
        for _, row in df_prod.iterrows():
            if pd.notna(row.get("Name")):
                p_name = str(row["Name"]).strip()
                product_dict[p_name] = {
                    "Price": float(row.get("Price", 0.00)),
                    "Cost": float(row.get("Cost", 0.00)),
                    "Description": str(row.get("Description", "")).replace("nan", "")
                }
    except:
        pass

uploaded_products = st.sidebar.file_uploader("📦 Upload/Sync QB Product List (CSV)", type=["csv"])
if uploaded_products:
    try:
        df_prod_new = pd.read_csv(uploaded_products)
        df_prod_new.columns = df_prod_new.columns.str.strip()
        prod_col = next((c for c in ["Product/Service Name", "Product/Service", "Item", "Name"] if c in df_prod_new.columns), df_prod_new.columns[0])
        price_col = next((c for c in ["Price", "Rate", "Sales Price"] if c in df_prod_new.columns), None)
        cost_col = next((c for c in ["Cost", "Purchase Cost"] if c in df_prod_new.columns), None)
        desc_col = next((c for c in ["Sales Description", "Description"] if c in df_prod_new.columns), None)
        
        prices_clean = []
        costs_clean = []
        for v in df_prod_new[price_col] if price_col else []:
            try: prices_clean.append(float(str(v).replace('$', '').replace(',', '').strip()))
            except: prices_clean.append(0.00)
        for v in df_prod_new[cost_col] if cost_col else []:
            try: costs_clean.append(float(str(v).replace('$', '').replace(',', '').strip()))
            except: costs_clean.append(0.00)
                
        clean_prod = pd.DataFrame({
            "Name": df_prod_new[prod_col], "Price": prices_clean if price_col else 0.00,
            "Cost": costs_clean if cost_col else 0.00, "Description": df_prod_new[desc_col].fillna("") if desc_col else ""
        })
        clean_prod.to_csv(PROD_FILE_PATH, index=False)
        st.sidebar.success("Saved inventory items permanently!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error processing inventory: {e}")

# ADD PRODUCT ON THE FLY
with st.sidebar.expander("📦 ➕ Add New Product on the Fly"):
    with st.form("add_product_form", clear_on_submit=True):
        new_prod_name = st.text_input("Product/Service Name")
        new_prod_price = st.number_input("Sales Price ($)", min_value=0.0, step=0.01)
        new_prod_cost = st.number_input("Purchase Cost ($)", min_value=0.0, step=0.01)
        new_prod_desc = st.text_area("Sales Description")
        submit_prod = st.form_submit_button("💾 Save Product to DB")
        if submit_prod:
            if new_prod_name.strip():
                df_p = pd.read_csv(PROD_FILE_PATH) if os.path.exists(PROD_FILE_PATH) else pd.DataFrame(columns=["Name", "Price", "Cost", "Description"])
                df_p = df_p[df_p["Name"].astype(str).str.strip() != new_prod_name.strip()]
                new_row = pd.DataFrame([{
                    "Name": new_prod_name.strip(), "Price": new_prod_price,
                    "Cost": new_prod_cost, "Description": new_prod_desc.strip()
                }])
                df_p = pd.concat([df_p, new_row], ignore_index=True)
                df_p.to_csv(PROD_FILE_PATH, index=False)
                st.toast(f"Product '{new_prod_name}' appended to database!", icon="📦")
                st.rerun()
            else:
                st.sidebar.error("Product name cannot be blank.")

# REMOVE PRODUCT FROM DB PERMANENTLY
if product_dict:
    with st.sidebar.expander("📦 ❌ Remove Product from DB"):
        with st.form("remove_product_form", clear_on_submit=True):
            prod_to_remove = st.selectbox("Select Product to Delete permanently", ["-- Select Product --"] + list(product_dict.keys()))
            submit_remove_prod = st.form_submit_button("🗑️ Delete Product from System DB")
            if submit_remove_prod and prod_to_remove != "-- Select Product --":
                df_p = pd.read_csv(PROD_FILE_PATH) if os.path.exists(PROD_FILE_PATH) else pd.DataFrame(columns=["Name", "Price", "Cost", "Description"])
                df_p = df_p[df_p["Name"].astype(str).str.strip() != prod_to_remove.strip()]
                df_p.to_csv(PROD_FILE_PATH, index=False)
                st.toast(f"Product '{prod_to_remove}' deleted permanently from local dictionary!", icon="🗑️")
                st.rerun()

if product_dict:
    st.sidebar.info(f"📦 Loaded {len(product_dict)} items with descriptions.")


# --- 💾 DOCUMENT STORAGE & RETRIEVAL WORKSPACES ---
st.sidebar.markdown("---")
st.sidebar.header("💾 Document Storage Database")

doc_db = load_document_db()

if st.sidebar.button("💾 Save / Update Current Document", use_container_width=True):
    if st.session_state.doc_id.strip():
        current_record = {
            "doc_type": st.session_state.doc_type,
            "doc_id": st.session_state.doc_id,
            "doc_date": st.session_state.doc_date.strftime("%Y-%m-%d") if hasattr(st.session_state.doc_date, 'strftime') else str(st.session_state.doc_date),
            "terms": st.session_state.terms,
            "due_date": st.session_state.due_date.strftime("%Y-%m-%d") if hasattr(st.session_state.due_date, 'strftime') else str(st.session_state.due_date),
            "cust_name": st.session_state.cust_name,
            "cust_email": st.session_state.cust_email,
            "bin_number": st.session_state.bin_number,
            "tax_rate": st.session_state.tax_rate,
            "currency": st.session_state.currency,
            "invoice_data": st.session_state.invoice_data
        }
        doc_db[st.session_state.doc_id.strip()] = current_record
        save_document_db(doc_db)
        st.sidebar.success(f"Successfully saved ID: {st.session_state.doc_id}")
        st.rerun()
    else:
        st.sidebar.error("Error: Document Identification number cannot be blank.")

if doc_db:
    saved_refs = list(doc_db.keys())
    selected_saved_ref = st.sidebar.selectbox("Select a Saved Document to Open", ["-- Choose From Database --"] + saved_refs)
    if selected_saved_ref != "-- Choose From Database --":
        if st.sidebar.button("📂 Open Selected Document", use_container_width=True):
            loaded_rec = doc_db[selected_saved_ref]
            st.session_state.doc_type = loaded_rec.get("doc_type", "Invoice")
            st.session_state.doc_id = loaded_rec.get("doc_id", "")
            
            try:
                st.session_state.doc_date = datetime.datetime.strptime(loaded_rec.get("doc_date", ""), "%Y-%m-%d").date()
            except:
                st.session_state.doc_date = datetime.date.today()
                
            st.session_state.terms = loaded_rec.get("terms", "Due on Receipt")
            try:
                st.session_state.due_date = datetime.datetime.strptime(loaded_rec.get("due_date", ""), "%Y-%m-%d").date()
            except:
                st.session_state.due_date = datetime.date.today()
                
            st.session_state.cust_name = loaded_rec.get("cust_name", "")
            st.session_state.cust_email = loaded_rec.get("cust_email", "")
            st.session_state.bin_number = loaded_rec.get("bin_number", "")
            st.session_state.tax_rate = float(loaded_rec.get("tax_rate", 13.0))
            st.session_state.currency = loaded_rec.get("currency", "$")
            
            # Legacy Schema Adaptation & Migration Logic
            raw_invoice_data = loaded_rec.get("invoice_data", {})
            if "Unit Price" in raw_invoice_data and "Item Amount" not in raw_invoice_data:
                raw_invoice_data["Item Amount"] = raw_invoice_data.pop("Unit Price")
            if "Item Tax Code" in raw_invoice_data and "Sales Tax" not in raw_invoice_data:
                raw_invoice_data["Sales Tax"] = raw_invoice_data.pop("Item Tax Code")
            if "Sales Tax" not in raw_invoice_data:
                raw_invoice_data["Sales Tax"] = ["HST"] * len(raw_invoice_data.get("Product", []))
                
            st.session_state.invoice_data = raw_invoice_data
            st.session_state.customer_select = "-- Manual Input / Select Customer --"
            st.sidebar.success(f"Loaded {selected_saved_ref} into workspace!")
            st.rerun()
else:
    st.sidebar.info("No documents archived in local database yet.")


# --- 🎨 SIDEBAR VISUAL DESIGN CONTROLS (WITH PERSISTENT APP STORAGE) ---
st.sidebar.header("🎨 PDF Document Styles")
theme_options = ["Deep Corporate Navy", "Modern Charcoal Black", "Forest Green", "Burgundy Red", "Custom Hex Code"]
try:
    theme_idx = theme_options.index(app_settings["theme_selection"])
except:
    theme_idx = 0

theme_selection = st.sidebar.selectbox("Brand Primary Color Theme", theme_options, index=theme_idx, key="theme_pref", on_change=save_app_settings)

if theme_selection == "Deep Corporate Navy":
    primary_color_hex = "#1A365D"
elif theme_selection == "Modern Charcoal Black":
    primary_color_hex = "#2D3748"
elif theme_selection == "Forest Green":
    primary_color_hex = "#1C4532"
elif theme_selection == "Burgundy Red":
    primary_color_hex = "#742A2A"
else:
    primary_color_hex = st.sidebar.color_picker("Pick your Custom Theme Color", value=app_settings["custom_color"], key="custom_color_pref", on_change=save_app_settings)

graphic_options = ["Modern Minimalist Lines", "Bold Solid Header Bar", "Full Operational Grid-Lines"]
try:
    graphic_idx = graphic_options.index(app_settings["graphic_style"])
except:
    graphic_idx = 0

graphic_style = st.sidebar.selectbox("Graphic Accents & Grid Style", graphic_options, index=graphic_idx, key="graphic_pref", on_change=save_app_settings)
show_total_background = st.sidebar.checkbox("Highlight totals box with light tint", value=app_settings["show_total_background"], key="total_bg_pref", on_change=save_app_settings)


# --- 📐 TABLE LAYOUT & POSITIONING ENGINE (WITH PERSISTENT APP STORAGE) ---
st.sidebar.markdown("---")
st.sidebar.header("📐 Table Layout & Positioning")
table_spacer_val = st.sidebar.slider("Vertical Space Before Table", min_value=0, max_value=150, value=int(app_settings["table_spacer_val"]), step=5, key="spacer_pref", on_change=save_app_settings, help="Moves the entire table down or up on the page.")
cell_padding_val = st.sidebar.slider("Row Padding (Top/Bottom)", min_value=2, max_value=25, value=int(app_settings["cell_padding_val"]), step=1, key="padding_pref", on_change=save_app_settings, help="Adjusts spacing inside the rows.")

# Fallback dynamic logic logic if layout has never been manual-saved before
default_width = app_settings["details_width"]
if default_width == -1:
    default_width = 250 if has_any_discount else 300

details_width = st.sidebar.slider("Item Details Column Width", min_value=150, max_value=420, value=int(default_width), step=5, key="width_pref", on_change=save_app_settings, help="Controls how wide the text column is. Other metrics adjust dynamically.")


# --- MAIN WORKSPACE HEADER SETUP ---
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("📄 Document Details")
    doc_options = ["Invoice", "Estimate", "Quotation"]
    doc_type = st.selectbox("Document Type", doc_options, key="doc_type")
    doc_id = st.text_input(f"{doc_type} No.", key="doc_id")
    doc_date = st.date_input("Invoice / Document Date", key="doc_date")
    terms_options = ["Due on Receipt", "Net 15", "Net 30", "Net 60", "Net 90"]
    terms = st.selectbox("Terms", terms_options, key="terms")
    due_date = st.date_input("Due Date", key="due_date")

with col2:
    st.subheader("👤 Customer Profile")
    if customer_dict:
        if "customer_select" not in st.session_state:
            st.session_state.customer_select = "-- Manual Input / Select Customer --"
            
        def on_customer_change():
            sel = st.session_state.customer_select
            if sel != "-- Manual Input / Select Customer --":
                st.session_state.cust_name = sel
                st.session_state.cust_email = customer_dict.get(sel, "")
                
        st.selectbox("QuickBooks Customer Directory", ["-- Manual Input / Select Customer --"] + list(customer_dict.keys()), key="customer_select", on_change=on_customer_change)
        
    cust_name = st.text_input("Customer Name", key="cust_name")
    cust_email = st.text_input("Customer Email", key="cust_email")

with col3:
    st.subheader("⚙️ Corporate Configurations")
    bin_number = st.text_input("BIN / Business Registration Number (Optional)", key="bin_number", placeholder="e.g. BIN 123456789RT0001")
    tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, step=0.5, key="tax_rate")
    currency = st.selectbox("Currency", ["$", "€", "£"], key="currency")

st.markdown("---")


# --- LINE ITEMS ENGINE (AUTOMATED PRICING & DESCRIPTION SYNC) ---
st.subheader("🛒 Document Line Items")

with st.container():
    ncol1, ncol2, ncol3, ncol4 = st.columns([2, 1, 1, 1])
    
    # 1. Product Directory Select Box
    if product_dict:
        with ncol1:
            selected_prod = st.selectbox("QuickBooks Product Inventory", ["-- Select a Product / Manual Entry --"] + list(product_dict.keys()))
            if selected_prod != "-- Select a Product / Manual Entry --":
                prod_name = st.text_input("Product/Service Name", value=selected_prod)
                auto_price = product_dict[selected_prod]["Price"]
                auto_desc = product_dict[selected_prod]["Description"]
            else:
                prod_name = st.text_input("Product/Service Name", value="")
                auto_price = 0.00
                auto_desc = ""
    else:
        with ncol1:
            prod_name = st.text_input("Product/Service Name")
        auto_price = 0.00
        auto_desc = ""

    # 2. Quantity Input Field
    with ncol2:
        qty = st.number_input("Quantity", min_value=1, value=1)
        
    # 3. Item Amount (Price) Input Field - Fully Overridable
    with ncol3:
        price = st.number_input("Item Amount", min_value=0.0, value=auto_price, step=1.0, help="Defaults to QB data but you can freely type a custom price here.")
        
    # 4. Tax Code Selection
    with ncol4:
        sales_tax = st.selectbox("Sales Tax", ["GST", "HST", "Exempt"], index=1, help="Select the specific sales tax protocol for this product line item.")

    prod_desc = st.text_area("Product Line Description / Scope of Work", value=auto_desc)

    apply_discount_to_line = st.checkbox("🏷️ Apply a discount to this specific item")
    if apply_discount_to_line:
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            disc_type = st.selectbox("Discount Type", ["Percentage (%)", "Amount ($)"])
        with dcol2:
            disc_val = st.number_input("Discount Value", min_value=0.0, value=0.0)
    else:
        disc_type = "None"
        disc_val = 0.0

    if st.button("➕ Add Line Item", use_container_width=True):
        if prod_name:
            if disc_type == "Percentage (%)":
                line_discount = (price * qty) * (disc_val / 100.0)
            elif disc_type == "Amount ($)":
                line_discount = disc_val
            else:
                line_discount = 0.0
            
            subtotal = (price * qty) - line_discount
            
            st.session_state.invoice_data["Product"].append(prod_name)
            st.session_state.invoice_data["Description"].append(prod_desc)
            st.session_state.invoice_data["Quantity"].append(qty)
            st.session_state.invoice_data["Item Amount"].append(price)
            st.session_state.invoice_data["Discount Type"].append(disc_type)
            st.session_state.invoice_data["Discount Given"].append(disc_val)
            st.session_state.invoice_data["Line Discount"].append(line_discount)
            st.session_state.invoice_data["Subtotal"].append(subtotal)
            st.session_state.invoice_data["Sales Tax"].append(sales_tax)
            st.rerun()

st.markdown("---")


# --- RENDER DATA TABLES & CORE OPERATIONAL TRANSLATION WORKFLOWS ---
if len(st.session_state.invoice_data["Product"]) > 0:
    df_display = pd.DataFrame(st.session_state.invoice_data)
    
    display_cols = ["Product", "Description", "Quantity", "Item Amount", "Sales Tax", "Subtotal"]
    if has_any_discount:
        display_cols = ["Product", "Description", "Quantity", "Item Amount", "Sales Tax", "Discount Given", "Subtotal"]
        
    st.dataframe(df_display[display_cols], use_container_width=True)
    
    # 🛠️ UNIFIED ACTIONS WORKSPACE (EDIT QUANTITY & PRICE, REORDER UP/DOWN, OR REMOVE)
    st.markdown("#### 🛠️ Line Item Actions Workspace (Edit, Reorder, or Remove)")
    
    manage_options = ["-- Choose an Item to Manage --"] + [
        f"{i+1}: {df_display['Product'].iloc[i]} (Qty: {df_display['Quantity'].iloc[i]}, Subtotal: {currency}{df_display['Subtotal'].iloc[i]:,.2f})"
        for i in range(len(df_display))
    ]
    selected_item_str = st.selectbox("Select an item from the current table list:", manage_options)
    
    m_col1, m_col2, m_col3 = st.columns([3, 2, 2])
    
    if selected_item_str != "-- Choose an Item to Manage --":
        idx = int(selected_item_str.split(":")[0]) - 1
        
        # COLUMN 1: EDIT QUANTITY & PRICE POST-ADDITION
        with m_col1:
            st.markdown("**✏️ Adjust Quantity & Price**")
            current_qty_val = int(st.session_state.invoice_data["Quantity"][idx])
            current_price_val = float(st.session_state.invoice_data["Item Amount"][idx])
            
            new_qty_input = st.number_input("Modify Quantity", min_value=1, value=current_qty_val, key=f"manage_qty_{idx}")
            new_price_input = st.number_input("Modify Item Price ($)", min_value=0.0, value=current_price_val, step=1.0, key=f"manage_price_{idx}")
            
            if st.button("💾 Save Line Item Changes", use_container_width=True):
                d_type = st.session_state.invoice_data["Discount Type"][idx]
                d_given = st.session_state.invoice_data["Discount Given"][idx]
                
                # Re-calculate correct item discounts using updated price metrics
                if d_type == "Percentage (%)":
                    new_line_discount = (new_price_input * new_qty_input) * (d_given / 100.0)
                elif d_type == "Amount ($)":
                    new_line_discount = d_given
                else:
                    new_line_discount = 0.0
                    
                st.session_state.invoice_data["Quantity"][idx] = new_qty_input
                st.session_state.invoice_data["Item Amount"][idx] = new_price_input
                st.session_state.invoice_data["Line Discount"][idx] = new_line_discount
                st.session_state.invoice_data["Subtotal"][idx] = (new_price_input * new_qty_input) - new_line_discount
                st.toast("Line item parameters updated successfully!", icon="✏️")
                st.rerun()
                
        # COLUMN 2: SHIFT UP / SHIFT DOWN POSITION
        with m_col2:
            st.markdown("**↕️ Reorder Location Position**")
            up_disabled = (idx == 0)
            down_disabled = (idx == len(df_display) - 1)
            
            uc1, uc2 = st.columns(2)
            with uc1:
                if st.button("⬆️ Move Up", use_container_width=True, disabled=up_disabled):
                    for key in st.session_state.invoice_data.keys():
                        st.session_state.invoice_data[key][idx], st.session_state.invoice_data[key][idx - 1] = \
                            st.session_state.invoice_data[key][idx - 1], st.session_state.invoice_data[key][idx]
                    st.toast("Item position moved up!", icon="⬆️")
                    st.rerun()
            with uc2:
                if st.button("⬇️ Move Down", use_container_width=True, disabled=down_disabled):
                    for key in st.session_state.invoice_data.keys():
                        st.session_state.invoice_data[key][idx], st.session_state.invoice_data[key][idx + 1] = \
                            st.session_state.invoice_data[key][idx + 1], st.session_state.invoice_data[key][idx]
                    st.toast("Item position moved down!", icon="⬇️")
                    st.rerun()
                    
        # COLUMN 3: SINGLE REMOVAL FROM QUOTE
        with m_col3:
            st.markdown("**❌ Delete Line Item**")
            st.markdown("<div style='padding-top:4px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Remove From Quote/Invoice", use_container_width=True):
                for key in st.session_state.invoice_data.keys():
                    st.session_state.invoice_data[key].pop(idx)
                st.toast("Item removed from list successfully.", icon="🗑️")
                st.rerun()
    else:
        with m_col1:
            st.info("💡 Select an item above to unlock live quantity, custom pricing, and row position controls.")

    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("🚨 Wipe Out / Clear All Items Entirely", type="primary"):
        st.session_state.invoice_data = {
            "Product": [], "Description": [], "Quantity": [], "Item Amount": [], 
            "Discount Type": [], "Discount Given": [], "Line Discount": [], "Subtotal": [],
            "Sales Tax": []
        }
        st.rerun()

    # WORKFLOW TRANSITION STAGE CONTROL (With Automated Database Save Synchronization)
    if doc_type in ["Estimate", "Quotation"]:
        st.markdown("### ⚡ Official Conversion Dashboard")
        if st.button(f"✅ Client Accepted? Convert this {doc_type} into an Official Invoice & Sync", use_container_width=True):
            st.session_state.doc_type = "Invoice"
            
            # Auto update active record inside the database file as well
            db_sync = load_document_db()
            db_sync[st.session_state.doc_id.strip()] = {
                "doc_type": "Invoice",
                "doc_id": st.session_state.doc_id,
                "doc_date": st.session_state.doc_date.strftime("%Y-%m-%d") if hasattr(st.session_state.doc_date, 'strftime') else str(st.session_state.doc_date),
                "terms": st.session_state.terms,
                "due_date": st.session_state.due_date.strftime("%Y-%m-%d") if hasattr(st.session_state.due_date, 'strftime') else str(st.session_state.due_date),
                "cust_name": st.session_state.cust_name,
                "cust_email": st.session_state.cust_email,
                "bin_number": st.session_state.bin_number,
                "tax_rate": st.session_state.tax_rate,
                "currency": st.session_state.currency,
                "invoice_data": st.session_state.invoice_data
            }
            save_document_db(db_sync)
            st.toast("Document type updated to Invoice and written to database records!", icon="⚡")
            st.rerun()

    gross_subtotal = df_display["Subtotal"].sum()
    calculated_tax = gross_subtotal * (tax_rate / 100.0)
    final_grand_total = gross_subtotal + calculated_tax

    sc1, sc2 = st.columns([2, 1])
    with sc2:
        st.markdown(f"**Subtotal:** {currency}{gross_subtotal:,.2f}")
        st.markdown(f"**Tax ({tax_rate}%):** {currency}{calculated_tax:,.2f}")
        st.markdown(f"### **Grand Total:** {currency}{final_grand_total:,.2f}")

    # --- QUICKBOOKS NATIVE CSV BATCH IMPORT EXPORT PREPARATION ENGINE ---
    st.subheader("📤 Data Serialization & Export Actions")
    qb_export_rows = []
    for i in range(len(df_display)):
        qb_export_rows.append({
            "Invoice No.": doc_id,
            "Customer": cust_name,
            "Invoice Date": doc_date.strftime("%m/%d/%Y") if hasattr(doc_date, 'strftime') else str(doc_date),
            "Due Date": due_date.strftime("%m/%d/%Y") if hasattr(due_date, 'strftime') else str(due_date),
            "Terms": terms,
            "Item Product/Service": df_display["Product"].iloc[i],
            "Item Description": df_display["Description"].iloc[i],
            "Item Quantity": df_display["Quantity"].iloc[i],
            "Item Amount": df_display["Item Amount"].iloc[i],
            "Sales Tax": df_display["Sales Tax"].iloc[i],
            "Line Amount": df_display["Subtotal"].iloc[i],
            "Taxable": "Taxable" if df_display["Sales Tax"].iloc[i] != "Exempt" else "Non-Taxable",
            "Tax Rate ID": f"Tax {tax_rate}%"
        })
    df_qb_export = pd.DataFrame(qb_export_rows)
    qb_csv_buffer = df_qb_export.to_csv(index=False).encode('utf-8')

    # --- REPORTLAB GENERATION BLOCK ---
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    brand_primary = colors.HexColor(primary_color_hex)
    accent_light_tint = colors.HexColor("#F7FAFC") if show_total_background else colors.white
    
    brand_style = ParagraphStyle('Brand', parent=styles['Heading1'], textColor=brand_primary, fontSize=24, spaceAfter=2)
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], spaceAfter=4, fontSize=10)
    desc_p_style = ParagraphStyle('DescStyle', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor("#2D3748"))
    desc_standalone_style = ParagraphStyle('DescStandalone', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#4A5568"), leftIndent=15, rightIndent=15, spaceAfter=6, spaceBefore=2)
    
    story = []
    
    if graphic_style == "Bold Solid Header Bar":
        banner_table = Table([[""]], colWidths=[540], rowHeights=[8])
        banner_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), brand_primary)]))
        story.append(banner_table)
        story.append(Spacer(1, 15))
        
    story.append(Paragraph(f"<b>{BUSINESS_CONFIG['company_name']}</b>", brand_style))
    
    company_info_text = f"{BUSINESS_CONFIG['address_line1']}, {BUSINESS_CONFIG['address_line2']}, {BUSINESS_CONFIG['postal_code']}"
    if bin_number.strip():
        company_info_text += f" | <b>{bin_number.strip()}</b>"
        
    story.append(Paragraph(company_info_text, meta_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(f"<b>{doc_type.upper()}</b>", ParagraphStyle('DocTitle', parent=styles['Heading2'], textColor=brand_primary, spaceAfter=8)))
    story.append(Paragraph(f"<b>{doc_type} No:</b> {doc_id}", meta_style))
    story.append(Paragraph(f"<b>Invoice Date:</b> {doc_date.strftime('%B %d, %Y') if hasattr(doc_date, 'strftime') else str(doc_date)}", meta_style))
    story.append(Paragraph(f"<b>Terms:</b> {terms}", meta_style))
    story.append(Paragraph(f"<b>Due Date:</b> {due_date.strftime('%B %d, %Y') if hasattr(due_date, 'strftime') else str(due_date)}", meta_style))
    story.append(Paragraph(f"<b>Client Name:</b> {cust_name} ({cust_email})", meta_style))
    
    # Dynamic Table Vertical Alignment Controls
    story.append(Spacer(1, table_spacer_val))
    
    # Dynamic Column Width Allocator Engine for PDF Grid Mapping
    if has_any_discount:
        rem_width = 540 - details_width
        col_widths = [
            details_width,
            rem_width * (30 / 260),
            rem_width * (65 / 260),
            rem_width * (45 / 260),
            rem_width * (55 / 260),
            rem_width * (65 / 260)
        ]
        header_data = [["Item Details", "Qty", "Item Amount", "Sales Tax", "Discount", "Total"]]
    else:
        rem_width = 540 - details_width
        col_widths = [
            details_width,
            rem_width * (35 / 210),
            rem_width * (75 / 210),
            rem_width * (45 / 210),
            rem_width * (55 / 210)
        ]
        header_data = [["Item Details", "Qty", "Item Amount", "Sales Tax", "Total"]]
        
    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), brand_primary),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),      
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),    
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), cell_padding_val),
        ('TOPPADDING', (0, 0), (-1, -1), cell_padding_val),
    ]))
    story.append(header_table)
    
    # Process line items sequentially as individual flowing modules to allow multi-page page breaks
    for i in range(len(df_display)):
        item_name_p = Paragraph(f"<b>{df_display['Product'].iloc[i]}</b>", desc_p_style)
        
        if has_any_discount:
            grid_val = df_display['Discount Given'].iloc[i]
            disc_label = f"-{currency}{df_display['Line Discount'].iloc[i]:.2f}" if df_display['Discount Type'].iloc[i] == "Amount ($)" else f"{grid_val}%"
            row_data = [[
                item_name_p, 
                str(df_display["Quantity"].iloc[i]),
                f"{currency}{df_display['Item Amount'].iloc[i]:,.2f}",
                str(df_display["Sales Tax"].iloc[i]),
                disc_label if grid_val > 0 else "", 
                f"{currency}{df_display['Subtotal'].iloc[i]:,.2f}"
            ]]
        else:
            row_data = [[
                item_name_p, 
                str(df_display["Quantity"].iloc[i]),
                f"{currency}{df_display['Item Amount'].iloc[i]:,.2f}",
                str(df_display["Sales Tax"].iloc[i]),
                f"{currency}{df_display['Subtotal'].iloc[i]:,.2f}"
            ]]
            
        item_table = Table(row_data, colWidths=col_widths)
        
        item_styles = [
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),      
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),    
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), cell_padding_val),
            ('TOPPADDING', (0, 0), (-1, -1), cell_padding_val),
        ]
        
        if graphic_style == "Full Operational Grid-Lines":
            item_styles.append(('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey))
        elif graphic_style == "Modern Minimalist Lines":
            item_styles.append(('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey))
        else:
            item_styles.append(('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")))
            
        item_table.setStyle(TableStyle(item_styles))
        story.append(item_table)
        
        # standalone flowable paragraph can naturally split across document frames safely
        desc_text = df_display['Description'].iloc[i]
        if desc_text and str(desc_text).strip():
            clean_desc = str(desc_text).replace("\n", "<br/>")
            desc_paragraph = Paragraph(clean_desc, desc_standalone_style)
            story.append(desc_paragraph)
            
        if graphic_style != "Full Operational Grid-Lines":
            story.append(Spacer(1, 4))
            
    # Totals Section Block
    totals_data = []
    empty_cells_count = 4 if has_any_discount else 3
    totals_data.append([""] * empty_cells_count + ["Subtotal:", f"{currency}{gross_subtotal:,.2f}"])
    totals_data.append([""] * empty_cells_count + [f"Tax ({tax_rate}%):", f"{currency}{calculated_tax:,.2f}"])
    totals_data.append([""] * empty_cells_count + ["Grand Total:", f"{currency}{final_grand_total:,.2f}"])
    
    totals_table = Table(totals_data, colWidths=col_widths)
    
    totals_styles = [
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), cell_padding_val),
        ('TOPPADDING', (0, 0), (-1, -1), cell_padding_val),
        ('LINEABOVE', (-2, 0), (-1, 0), 1, brand_primary),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    
    if show_total_background:
        totals_styles.append(('BACKGROUND', (-2, 0), (-1, -1), accent_light_tint))
        
    totals_table.setStyle(TableStyle(totals_styles))
    story.append(Spacer(1, 10))
    story.append(totals_table)
    
    doc.build(story)
    pdf_data = pdf_buffer.getvalue()

    # Actions Display Panel
    xc1, xc2 = st.columns(2)
    with xc1:
        st.download_button(label="📥 Export QuickBooks Batch Template (.CSV)", data=qb_csv_buffer, file_name=f"qb_batch_import_{doc_id}.csv", mime="text/csv", use_container_width=True)
    with xc2:
        st.download_button(label="📄 Download Client PDF Document (.PDF)", data=pdf_data, file_name=f"{doc_type}_{doc_id}.pdf", mime="application/pdf", use_container_width=True)

    # Email Delivery engine
    st.subheader("✉️ SMTP Electronic Delivery Portal")
    with st.expander("Configure Email & Send Instantly"):
        ec1, ec2 = st.columns(2)
        with ec1:
            smtp_server = st.text_input("SMTP Server Host", value=SMTP_SERVER_DEFAULT)
            smtp_port = st.number_input("SMTP Network Port", value=int(SMTP_PORT_DEFAULT))
            sender_email = st.text_input("Your Corporate Email Account", value=SENDER_EMAIL_DEFAULT)
            sender_password = st.text_input("Your Email Security App Password", type="password", value=SENDER_PASSWORD_DEFAULT)
        with ec2:
            email_subject = st.text_input("Subject String", value=f"Your {doc_type} Reference: {doc_id}")
            cc_email = st.text_input("CC Email Address (Optional)", value="", placeholder="e.g. office@sensiblehifi.com, info@sensiblehifi.com")
            email_body = st.text_area("Email Content Body", value=f"Hi {cust_name},\n\nPlease find attached your formal {doc_type.lower()} ({doc_id}) generated for review.\n\nBest Regards,\n{BUSINESS_CONFIG['company_name']} Team")
        
        if st.button("🚀 Transmit Email Document to Client", use_container_width=True):
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = cust_email
                
                # Dynamic Routing Initialization
                recipients = [cust_email.strip()]
                if cc_email.strip():
                    msg['Cc'] = cc_email.strip()
                    cc_list = [c.strip() for c in cc_email.split(",") if c.strip()]
                    recipients.extend(cc_list)
                    
                msg['Subject'] = email_subject
                msg.attach(MIMEText(email_body, 'plain'))
                
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(pdf_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename={doc_type}_{doc_id}.pdf")
                msg.attach(part)
                
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())
                server.quit()
                st.success(f"Transmission Success! Delivered securely to {cust_email} and all CC'd channels.")
            except Exception as e:
                st.error(f"Network Connection Failed: Verify settings. Details: {e}")
else:
    st.info("🛒 Your document is currently empty. Use the form above to add your first line item!")
