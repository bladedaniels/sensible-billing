import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- SLEEK UX CONFIGURATION & BRANDING ---
st.set_page_config(page_title="SENSIBLE HIFI Studio", page_icon="🔊", layout="wide")

# Premium Modern Web Styling (Inspired by Zoho/QuoteIQ minimal card system)
st.markdown(""", unsafe_allow_html=True)
<style>
    /* Global Background and Typography */
    .stApp { background-color: #F8FAFC; }
    h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important; }
    
    /* Branding Header Card */
    .brand-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 30px;
        border-radius: 16px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .brand-title { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.05em; }
    .brand-subtitle { font-size: 1rem; color: #94A3B8; margin-top: 5px; }

    /* Modern Minimalist Cards */
    .invoice-card {
        background-color: white;
        padding: 24px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05);
        margin-bottom: 20px;
    }
    
    /* Status Badges */
    .badge {
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-paid { background-color: #DCFCE7; color: #15803D; }
    .badge-sent { background-color: #DBEAFE; color: #1D4ED8; }
    .badge-draft { background-color: #F1F5F9; color: #475569; }

    /* Custom Input Wrapper for Mobile Touch */
    div.stSelectbox, div.stNumberInput, div.stTextInput {
        margin-bottom: 15px !important;
    }
    
    /* Sleek Primary Action Buttons */
    .stButton>button {
        background-color: #2563EB !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1D4ED8 !important;
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)
# --- DATABASE / STATE CONTROLLER ---
if 'clients' not in st.session_state:
    st.session_state.clients = pd.DataFrame(columns=["Client Name", "Email", "Phone"])
if 'products' not in st.session_state:
    st.session_state.products = pd.DataFrame(columns=["Product/Service", "Rate"])
if 'documents' not in st.session_state:
    st.session_state.documents = []

# --- TOP BRANDING BLOCK ---
st.markdown("""
    <div class="brand-banner">
        <div class="brand-title">🔊 SENSIBLE HIFI</div>
        <div class="brand-subtitle">Billing Studio & Client Ledger</div>
    </div>
""", unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["⚡ Quick Bill", "📂 Data Vault", "📜 Ledger & QB Export"])

# ==========================================
# TAB 1: QUICK BILLING COMPONENT (Zoho Style)
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("### 📝 Build Document")
        doc_type = st.segmented_control("Type", ["Estimate", "Invoice"], default="Estimate")
        
        # Smart Client Dropdown
        if not st.session_state.clients.empty:
            client_options = st.session_state.clients["Client Name"].tolist()
            selected_client = st.selectbox("Client Account", client_options)
            client_email = st.session_state.clients[st.session_state.clients["Client Name"] == selected_client]["Email"].values[0]
        else:
            selected_client = st.text_input("Client Name", placeholder="e.g. John Doe")
            client_email = st.text_input("Client Email", placeholder="e.g. john@domain.com")
            
        # Smart Product Dropdown
        if not st.session_state.products.empty:
            prod_options = st.session_state.products["Product/Service"].tolist()
            selected_prod = st.selectbox("Line Item / Service", prod_options)
            default_rate = float(st.session_state.products[st.session_state.products["Product/Service"] == selected_prod]["Rate"].values[0])
        else:
            selected_prod = st.text_input("Service Rendered", placeholder="e.g. Custom Audio Calibration")
            default_rate = 0.0
            
        rate = st.number_input("Unit Rate ($)", min_value=0.0, value=default_rate)
        qty = st.number_input("Quantity", min_value=1, value=1)
        amount = qty * rate

    with col2:
        st.markdown("### 📱 Live Preview")
        
        status_class = "badge-sent" if doc_type == "Invoice" else "badge-draft"
        status_label = "SENT/ACTIVE" if doc_type == "Invoice" else "DRAFT"
        
        st.markdown(f"""
        <div class="invoice-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: #0F172A; font-size: 1.1rem;">{doc_type.upper()}</span>
                <span class="badge {status_class}">{status_label}</span>
            </div>
            <div style="margin-top: 15px; color: #475569; font-size: 0.9rem;">
                <p style="margin: 2px 0;"><strong>Client:</strong> {selected_client}</p>
                <p style="margin: 2px 0;"><strong>Email:</strong> {client_email}</p>
                <p style="margin: 2px 0;"><strong>Issued:</strong> {datetime.today().date()}</p>
            </div>
            <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; font-size: 0.95rem; color: #0F172A;">
                <span>{selected_prod} (x{qty})</span>
                <span style="font-weight: 600;">${amount:,.2f}</span>
            </div>
            <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <span style="font-size: 0.9rem; color: #64748B;">Total Amount Due</span>
                <span style="font-size: 1.75rem; font-weight: 800; color: #0F172A;">${amount:,.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        attach_pay = st.checkbox("Generate Payment Link", value=True)
        
        if st.button(f"Finalize & Record {doc_type}"):
            if selected_client and selected_prod:
                doc_id = f"SH-{1000 + len(st.session_state.documents)}"
                pay_url = f"https://checkout.stripe.com/pay/placeholder_{doc_id}" if attach_pay else "N/A"
                
                st.session_state.documents.append({
                    "Doc ID": doc_id,
                    "Type": doc_type,
                    "Client": selected_client,
                    "Email": client_email,
                    "Item": selected_prod,
                    "Amount": amount,
                    "Status": "Sent" if doc_type == "Invoice" else "Draft/Estimate",
                    "Date": datetime.now().strftime('%Y-%m-%d'),
                    "Payment Link": pay_url
                })
                st.success(f"{doc_type} saved successfully to Ledger!")
            else:
                st.error("Missing mandatory Client Name or Item data.")

# ==========================================
# TAB 2: DATA VAULT (CSV Multi-Importer)
# ==========================================
with tab2:
    st.markdown("### 📥 Cloud Spread Data Sync")
    st.write("Import files directly into your active dashboard memory instantly.")
    
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(""", unsafe_allow_html=True)        <div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;">
            <strong>Accounts Matrix (Clients)</strong><br>
            <span style="font-size:0.8rem; color:#64748B;">Required Columns: Client Name, Email</span>
        </div>
        """, unsafe_allow_html=True)
        c_file = st.file_uploader("Select Client File", type="csv", label_visibility="collapsed")
        if c_file:
            df = pd.read_csv(c_file)
            if "Client Name" in df.columns and "Email" in df.columns:
                st.session_state.clients = df[["Client Name", "Email"]]
                st.success(f"Linked {len(df)} client records!")
            else:
                st.error("Header mismatch. Missing 'Client Name' or 'Email'.")

    with c2:
        st.markdown(""", unsafe_allow_html=True)
        <div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;">
            <strong>SKU / Price Book (Products)</strong><br>
            <span style="font-size:0.8rem; color:#64748B;">Required Columns: Product/Service, Rate</span>
        </div>
        """, unsafe_allowed_html=True)
        p_file = st.file_uploader("Select Product File", type="csv", label_visibility="collapsed")
        if p_file:
            df = pd.read_csv(p_file)
            if "Product/Service" in df.columns and "Rate" in df.columns:
                st.session_state.products = df[["Product/Service", "Rate"]]
                st.success(f"Linked {len(df)} catalog items!")
            else:
                st.error("Header mismatch. Missing 'Product/Service' or 'Rate'.")

# ==========================================
# TAB 3: STREAMLINED CARD LEDGER & QB EXPORT
# ==========================================
with tab3:
    st.markdown("### 📊 Live Transaction Ledger")
    
    if st.session_state.documents:
        df_docs = pd.DataFrame(st.session_state.documents)
        
        # Build Sleek Grid Cards instead of ugly spreadsheets (QuoteIQ Style)
        for idx, row in df_docs.iterrows():
            badge_type = "badge-paid" if row['Status'] == "Paid" else ("badge-sent" if row['Status'] == "Sent" else "badge-draft")
            
            # Master Container Card for every transaction row
            st.markdown(f"""
            <div style="background-color: white; padding: 18px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 700; color: #0F172A;">{row['Doc ID']}</span> 
                        <span style="color:#64748B; font-size:0.85rem; margin-left: 10px;">{row['Date']}</span>
                    </div>
                    <span class="badge {badge_type}">{row['Status'].upper()}</span>
                </div>
                <div style="margin-top: 8px; font-size: 0.95rem; color: #334155;">
                    <strong>{row['Client']}</strong> — {row['Item']}
                </div>
                <div style="margin-top: 4px; font-size: 1.15rem; font-weight: 700; color: #0F172A;">
                    ${row['Amount']:,.2f}
                </div>
                {f'<div style="font-size:0.8rem; color:#2563EB; margin-top:6px;">🔗 Payment Portal Active</div>' if row['Payment Link'] != 'N/A' else ''}
            </div>
            """, unsafe_allow_html=True)
            
            # Operational Mini Action Panel directly under the card components
            act1, act2, _ = st.columns([1, 1, 3])
            if row['Type'] == "Estimate":
                with act1:
                    if st.button("Convert to Invoice", key=f"cnv_{idx}"):
                        st.session_state.documents[idx]['Type'] = "Invoice"
                        st.session_state.documents[idx]['Status'] = "Sent"
                        st.rerun()
            elif row['Status'] == "Sent":
                with act1:
                    if st.button("Mark as Paid", key=f"pd_{idx}"):
                        st.session_state.documents[idx]['Status'] = "Paid"
                        st.rerun()
            st.markdown("<br>", unsafe_allowed_html=True)
            
        # --- QUICKBOOKS SYNC EXPORTER ---
        st.markdown("### 🗃️ QuickBooks System Sync")
        st.write("Convert structural application rows into native QuickBooks Ledger columns.")
        
        qb_export_df = pd.DataFrame({
            "RefNumber": df_docs["Doc ID"],
            "TxnDate": df_docs["Date"],
            "Customer": df_docs["Client"],
            "Item": df_docs["Item"],
            "Amount": df_docs["Amount"],
            "Terms": "Net 30",
            "IncomeAccount": "Sales / Audio Configuration"
        })
        
        csv_io = io.StringIO()
        qb_export_df.to_csv(csv_io, index=False)
        
        st.download_button(
            label="Download QuickBooks Structured CSV",
            data=csv_io.getvalue(),
            file_name=f"SENSIBLE_QB_{datetime.now().strftime('%m%d%Y')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No documents currently on file. Use Tab 1 to build your first record.")
