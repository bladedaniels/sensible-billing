import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- ZOHO BLUEPRINT CONFIGURATION ---
st.set_page_config(page_title="Zoho Invoice Clone", page_icon="💼", layout="wide")

# Inject Premium Zoho CSS Layouts
st.markdown("""
    <style>
    /* Zoho Flat UI Foundations */
    .stApp { background-color: #F3F4F6; }
    
    /* Top Zoho Action Bar Ribbon */
    .zoho-header {
        background-color: #FFFFFF;
        padding: 15px 25px;
        border-bottom: 1px solid #E5E7EB;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .zoho-logo { color: #1E40AF; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.5px; }
    
    /* Premium Document Card Styling */
    .zoho-document-paper {
        background-color: #FFFFFF;
        padding: 40px;
        border-radius: 4px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border: 1px solid #E5E7EB;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Zoho Table Styling */
    .zoho-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 25px;
    }
    .zoho-table th {
        background-color: #374151;
        color: white;
        text-align: left;
        padding: 10px;
        font-size: 0.85rem;
    }
    .zoho-table td {
        padding: 12px 10px;
        border-bottom: 1px solid #E5E7EB;
        font-size: 0.9rem;
        color: #1F2937;
    }
    
    /* Status Pills */
    .p_badge {
        padding: 4px 10px;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .p_draft { background-color: #E5E7EB; color: #374151; }
    .p_sent { background-color: #DBEAFE; color: #1E40AF; }
    .p_paid { background-color: #D1FAE5; color: #065F46; }
    </style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE ---
if 'documents' not in st.session_state:
    # Seed data mimicking your Zoho account format
    st.session_state.documents = [
        {"id": "QT-00104", "type": "Quote", "client": "Toronto HiFi Sound", "email": "info@torontohifi.ca", "item": "Custom Calibration Hookup", "rate": 1250.00, "qty": 1, "status": "Sent", "date": "2026-06-10"},
        {"id": "QT-00103", "type": "Quote", "client": "Montreal Audio Lab", "email": "contact@mtlaudio.com", "item": "Acoustic Dampening Wall Layout", "rate": 890.00, "qty": 3, "status": "Draft", "date": "2026-06-08"}
    ]

# --- TOP CRM HEADER BANNER ---
st.markdown("""
    <div class="zoho-header">
        <div class="zoho-logo">⚙️ Zoho Invoice <span style="color:#6B7280; font-weight:400; font-size:1rem;">| Estimates & Quotes</span></div>
        <div style="font-size:0.85rem; color:#4B5563;">Sensible HiFi Studio Corporate Account</div>
    </div>
""", unsafe_allow_html=True)

# --- SPLIT LAYOUT ENGINE ---
sidebar_panel, visual_preview = st.columns([1, 2], gap="large")

# ==========================================
# LEFT PANEL: ZOHO REPOSITORY SIDEBAR
# ==========================================
with sidebar_panel:
    st.markdown("### 🔍 All Quotes")
    
    # Quick creation box
    with st.expander("➕ Create New Estimate/Quote", expanded=False):
        c_name = st.text_input("Customer Name")
        c_email = st.text_input("Customer Email")
        i_name = st.text_input("Line Item/SKU Description")
        i_rate = st.number_input("Rate per unit ($)", min_value=0.0, step=50.0)
        i_qty = st.number_input("Quantity Ordered", min_value=1, step=1)
        
        if st.button("Save as Draft"):
            if c_name and i_name:
                new_id = f"QT-00{105 + len(st.session_state.documents)}"
                st.session_state.documents.insert(0, {
                    "id": new_id, "type": "Quote", "client": c_name, "email": c_email,
                    "item": i_name, "rate": i_rate, "qty": i_qty, "status": "Draft",
                    "date": datetime.today().strftime('%Y-%m-%d')
                })
                st.success(f"{new_id} added to ledger grid.")
                st.rerun()

    st.markdown("---")
    
    # Vertical Card Selectors
    for idx, doc in enumerate(st.session_state.documents):
        badge_style = "p_sent" if doc['status'] == "Sent" else ("p_paid" if doc['status'] == "Paid" else "p_draft")
        
        # Selectable container element
        with st.container():
            st.markdown(f"""
            <div style="background-color: white; padding:15px; border-radius:6px; border-left: 5px solid #1E40AF; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-weight:700;">
                    <span style="color:#111827;">{doc['id']}</span>
                    <span style="color:#111827;">${(doc['rate']*doc['qty']):,.2f}</span>
                </div>
                <div style="font-size:0.85rem; color:#4B5563; margin-top:3px;">{doc['client']}</div>
                <div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;">
                    <span style="font-size:0.75rem; color:#9CA3AF;">{doc['date']}</span>
                    <span class="p_badge {badge_style}">{doc['status'].upper()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("View Live Sheet Details", key=f"sel_{doc['id']}"):
                st.session_state.active_index = idx

# Default to displaying the top item if nothing is selected yet
if 'active_index' not in st.session_state:
    st.session_state.active_index = 0

# Secure index lookup protection
active_idx = min(st.session_state.active_index, len(st.session_state.documents) - 1)
active_doc = st.session_state.documents[active_idx]

# ==========================================
# RIGHT PANEL: ZOHO DESK PRINT VIEW
# ==========================================
with visual_preview:
    # Ribbon Action Controls inside Preview Engine
    action_col1, action_col2, action_col3 = st.columns([2, 2, 4])
    with action_col1:
        if active_doc['status'] != "Paid":
            if st.button("⚡ Convert to Invoice", key="action_conv"):
                st.session_state.documents[active_idx]['status'] = "Paid"
                st.success("Converted status mapping smoothly.")
                st.rerun()
    with action_col2:
        if active_doc['status'] == "Draft":
            if st.button("✉️ Mark as Sent", key="action_sent"):
                st.session_state.documents[active_idx]['status'] = "Sent"
                st.rerun()

    # The Zoho Professional Core Paper Sheet Frame
    total_amount = active_doc['rate'] * active_doc['qty']
    
    st.markdown(f"""
    <div class="zoho-document-paper">
        <table style="width:100%; border:none;">
            <tr>
                <td style="border:none; padding:0; vertical-align:top;">
                    <h2 style="margin:0; color:#1E40AF;">🔊 SENSIBLE HIFI</h2>
                    <p style="font-size:0.85rem; color:#6B7280; margin:4px 0;">Ontario, Canada</p>
                </td>
                <td style="border:none; padding:0; text-align:right; vertical-align:top;">
                    <h1 style="margin:0; font-size:2rem; color:#374151; font-weight:300;">ESTIMATE</h1>
                    <p style="margin:4px 0; font-size:0.9rem;"><strong>Estimate #:</strong> {active_doc['id']}</p>
                    <p style="margin:4px 0; font-size:0.9rem; color:#6B7280;"><strong>Date:</strong> {active_doc['date']}</p>
                </td>
            </tr>
        </table>
        
        <div style="margin-top: 40px; font-size:0.9rem;">
            <p style="color:#6B7280; margin-bottom:5px; text-transform: uppercase; font-size:0.75rem; letter-spacing:1px;"><strong>Bill To:</strong></p>
            <p style="margin:2px 0; font-size:1rem; color:#111827;"><strong>{active_doc['client']}</strong></p>
            <p style="margin:2px 0; color:#4B5563;">{active_doc['email']}</p>
        </div>
        
        <table class="zoho-table">
            <thead>
                <tr>
                    <th>Item & Description</th>
                    <th style="text-align:right; width:15%;">Rate</th>
                    <th style="text-align:right; width:10%;">Qty</th>
                    <th style="text-align:right; width:20%;">Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>{active_doc['item']}</strong><br><span style="font-size:0.75rem; color:#6B7280;">Standard Audio Setup Verification Logistics</span></td>
                    <td style="text-align:right;">${active_doc['rate']:,.2f}</td>
                    <td style="text-align:right;">{active_doc['qty']}</td>
                    <td style="text-align:right; font-weight:600;">${total_amount:,.2f}</td>
                </tr>
            </tbody>
        </table>
        
        <div style="margin-top:30px; display:flex; justify-content:flex-end;">
            <table style="width:40%; border-collapse:collapse;">
                <tr>
                    <td style="padding:8px 0; border:none; color:#4B5563;">Sub Total</td>
                    <td style="padding:8px 0; border:none; text-align:right; font-weight:600;">${total_amount:,.2f}</td>
                </tr>
                <tr style="border-top:1px solid #E5E7EB; border-bottom:1px solid #111827;">
                    <td style="padding:12px 0; font-size:1.1rem; font-weight:700; color:#111827;">Total ($)</td>
                    <td style="padding:12px 0; font-size:1.1rem; font-weight:700; text-align:right; color:#1E40AF;">${total_amount:,.2f}</td>
                </tr>
            </table>
        </div>
        
        <div style="margin-top:60px; border-top:1px solid #F3F4F6; padding-top:15px; font-size:0.8rem; color:#9CA3AF;">
            <p style="margin:0;">Notes: Terms set at Net 30 default execution. Thank you for your business!</p>
        </div>
    </div>
""", unsafe_allow_html=True)
