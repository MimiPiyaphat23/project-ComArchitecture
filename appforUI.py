import streamlit as st
import pandas as pd
import time
import io

try:
    from core.parser import parse_instructions
    from core.pipeline_engine import Pipeline
    from performance.metrics import calculate_metrics as _calc_metrics_orig
except ImportError as e:
    st.error(f"❌ ไม่สามารถโหลด Core Logic ได้: {e}")

def calculate_metrics(timeline):
    """Fixed version — นับ cycle จาก WB last - IF first + 1"""
    if not timeline:
        return {"cycles": 0, "cpi": 0, "instructions": 0, "stalls": 0}
    stages = ["IF", "ID", "EX", "MEM", "WB"]

    # กรอง trailing empty rows ออก
    active = [r for r in timeline
              if any(str(r.get(s,"")).strip() not in ("","STALL") for s in stages)]
    if not active:
        return {"cycles": 0, "cpi": 0, "instructions": 0, "stalls": 0}

    # total_cycles = จำนวน active rows (แต่ละ row = 1 cycle จริงๆ)
    total_cycles = len(active)

    # นับ instruction ที่ผ่าน WB
    instructions_done = set()
    stall_count = 0
    for i, row in enumerate(active):
        wb = str(row.get("WB","")).strip()
        if wb and wb != "STALL":
            instructions_done.add(wb)
        # นับ stall: STALL string หรือ EX ว่างแต่ ID มีค่า หรือ ID ซ้ำ row ก่อน
        is_stall = any(str(row.get(s,"")).strip() == "STALL" for s in stages)
        if not is_stall and i > 0:
            id_curr = str(row.get("ID","")).strip()
            id_prev = str(active[i-1].get("ID","")).strip()
            if id_curr and id_curr not in ("","STALL") and id_curr == id_prev:
                is_stall = True
        if is_stall:
            stall_count += 1

    n = len(instructions_done)
    # fallback: นับจาก IF
    if n == 0:
        for row in active:
            v = str(row.get("IF","")).strip()
            if v and v != "STALL":
                instructions_done.add(v)
        n = len(instructions_done)

    cpi = round(total_cycles / n, 4) if n > 0 else 0
    return {"cycles": total_cycles, "cpi": cpi, "instructions": n, "stalls": stall_count}

st.set_page_config(page_title="RISC Pipeline Simulator", layout="wide", page_icon="🚀")

# ── Global font & UI styling ──────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, p, div, span {
    font-family: 'Inter', sans-serif !important;
}
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px;
}
label, .stCheckbox label p, .stRadio label p {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #374151 !important;
}
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
}
.stTextArea textarea {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
    border-radius: 8px !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #6B7280 !important;
}
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
}
.stAlert {
    border-radius: 8px !important;
}
/* expander styling */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    white-space: normal !important;
}
/* ลบ monospace จาก error box */
.stAlert p, .stAlert div {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
}
.stAlert code {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    background: transparent !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Global font & UI styling ──────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp, p, div, span, li {
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background: #f7f8fc !important;
}
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.4px;
    color: #1a1a2e;
}

/* ── Labels ── */
label, .stCheckbox label p, .stRadio label p, .stSlider label p {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #4B5563 !important;
}

/* ── Primary button → indigo ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: none !important;
    color: white !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35) !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99,102,241,0.45) !important;
}

/* ── Secondary buttons ── */
.stButton > button:not([kind="primary"]) {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 8px !important;
    border: 1.5px solid #e0e7ff !important;
    color: #4338ca !important;
    background: white !important;
    transition: all 0.15s ease !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #eef2ff !important;
    border-color: #6366f1 !important;
}

/* ── Text area ── */
.stTextArea textarea {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 13.5px !important;
    line-height: 1.75 !important;
    border-radius: 10px !important;
    border: 1.5px solid #e5e7eb !important;
    background: #ffffff !important;
    color: #1f2937 !important;
    padding: 12px !important;
}
.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    background: #eef2ff !important;
    padding: 6px !important;
    border-radius: 14px !important;
    border: 1.5px solid #e0e7ff !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 9px !important;
    color: #818cf8 !important;
    padding: 7px 18px !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.18s ease !important;
    white-space: nowrap !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #e0e7ff !important;
    color: #4338ca !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #4338ca !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.18) !important;
    border: 1px solid #e0e7ff !important;
}
/* ซ่อน underline เดิมของ Streamlit */
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── Metric ── */
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #6B7280 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    font-weight: 800 !important;
    font-size: 2rem !important;
    color: #1a1a2e !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border-radius: 10px !important;
    border: 1px solid #e5e7eb !important;
    overflow: hidden !important;
}

/* ── Alert boxes ── */
.stAlert {
    border-radius: 10px !important;
    font-size: 13.5px !important;
}
.stAlert code {
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    background: transparent !important;
    padding: 0 !important;
}

/* ── Divider ── */
hr {
    border-color: #e5e7eb !important;
    margin: 16px 0 !important;
}

/* ── expander styling ── */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    white-space: normal !important;
}

/* ── Caption ── */
.stCaption, small {
    font-size: 12px !important;
    color: #9CA3AF !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
STAGE_COLORS = {
    "IF": "#4FC3F7", "ID": "#81C784", "EX": "#FFD54F",
    "MEM": "#FFB74D", "WB": "#E57373", "STALL": "#B0BEC5", "": "#f0f0f0",
}
REG_NAMES = [
    "$zero","$at","$v0","$v1","$a0","$a1","$a2","$a3",
    "$t0","$t1","$t2","$t3","$t4","$t5","$t6","$t7",
    "$s0","$s1","$s2","$s3","$s4","$s5","$s6","$s7",
    "$t8","$t9","$k0","$k1","$gp","$sp","$fp","$ra",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def extract_instr_list(df):
    all_instrs = []
    for s in STAGES:
        if s in df.columns:
            for v in df[s].dropna().unique():
                if v and str(v).strip() not in ("", "STALL") and v not in all_instrs:
                    all_instrs.append(v)
    if not all_instrs:
        for col in ["instruction", "Instruction", "instr"]:
            if col in df.columns:
                return df[col].dropna().unique().tolist()
    return all_instrs

def normalize_df(df):
    if "cycle" in df.columns and "Cycle" not in df.columns:
        df = df.rename(columns={"cycle": "Cycle"})
    if "Cycle" not in df.columns:
        df["Cycle"] = range(1, len(df) + 1)
    # กรอง cycle ที่ทุก stage ว่างออก (trailing empty cycles)
    stage_cols = [s for s in ["IF","ID","EX","MEM","WB"] if s in df.columns]
    if stage_cols:
        has_data = df[stage_cols].apply(
            lambda row: any(str(v).strip() not in ("", "STALL") for v in row), axis=1
        )
        df = df[has_data].reset_index(drop=True)
    return df

def count_stalls(df):
    """
    ตรวจ stall จาก 3 วิธี:
    1. มีค่า "STALL" ใน cell
    2. EX ว่าง แต่ ID ไม่ว่าง (bubble inserted — EX ควรมี instruction แต่ว่าง)
    3. ID ซ้ำกับ row ก่อนหน้า (instruction ถูก hold ใน ID stage)
    """
    total, details = 0, []
    rows = list(df.iterrows())
    for i, (_, row) in enumerate(rows):
        cycle = row.get("Cycle", "?")
        is_stall = False

        # วิธี 1: มี "STALL" string
        for s in STAGES:
            if str(row.get(s, "")).strip() == "STALL":
                is_stall = True
                break

        # วิธี 2: ID ซ้ำกับ row ก่อนหน้า = instruction ถูก hold (stall จริง)
        if not is_stall and i > 0:
            prev_row = rows[i-1][1]
            id_curr = str(row.get("ID", "")).strip()
            id_prev = str(prev_row.get("ID", "")).strip()
            if id_curr and id_curr not in ("", "STALL") and id_curr == id_prev:
                is_stall = True

        if is_stall:
            total += 1
            details.append({"Cycle": cycle, "Note": "bubble/stall detected"})

    return total, details

def detect_hazards(instr_list):
    """
    วิเคราะห์ RAW hazard จากชื่อ instruction
    คืนค่า dict: { (i, j): "RAW: $s0" } — i เขียน, j อ่าน
    """
    hazards = {}

    def parse_regs(raw):
        """ดึง register จาก string เช่น 'ADD $s0, $t1, $t2' → ['$s0','$t1','$t2']"""
        parts = raw.replace(",", "").split()
        return [p for p in parts[1:] if p.startswith("$")]

    def get_dest(raw):
        regs = parse_regs(raw)
        return regs[0] if regs else None

    def get_srcs(raw):
        regs = parse_regs(raw)
        return regs[1:] if len(regs) > 1 else []

    for i in range(len(instr_list)):
        dest = get_dest(instr_list[i])
        if not dest or dest == "$zero":
            continue
        for j in range(i + 1, min(i + 4, len(instr_list))):
            srcs = get_srcs(instr_list[j])
            if dest in srcs:
                hazards[(i, j)] = f"RAW: {dest}"

    return hazards

def build_animation_html(df, instr_list, current, max_c, hazard_pairs=None):
    if hazard_pairs is None:
        hazard_pairs = {}

    # สร้าง set ของ index ที่มี hazard เพื่อไฮไลต์ชื่อ instruction
    hazard_indices = set()
    for (i, j) in hazard_pairs:
        hazard_indices.add(i)
        hazard_indices.add(j)

    rows_html = ""
    for idx, instr in enumerate(instr_list):
        cells = ""
        for c in range(1, max_c + 1):
            stg = ""
            target = df[df["Cycle"] == c]
            if not target.empty:
                row = target.iloc[0]
                for s in STAGES:
                    if s in row and row[s] == instr:
                        stg = s
                        break
            is_current = (c == current)
            is_past    = (c < current)
            bg      = STAGE_COLORS.get(stg, "#f0f0f0") if stg else "#f0f0f0"
            opacity = "1.0" if is_current else ("0.4" if is_past else "0.06")
            border  = "2px solid #222" if (is_current and stg) else "1px solid #ddd"
            shadow  = "box-shadow:0 0 6px rgba(0,0,0,0.25);" if (is_current and stg) else ""
            label   = stg if (is_current or is_past) else ""
            cells += (
                f'<div style="width:48px;height:34px;background:{bg};opacity:{opacity};'
                f'border:{border};margin:2px;display:flex;justify-content:center;'
                f'align-items:center;font-size:11px;font-weight:bold;border-radius:6px;{shadow}">'
                f'{label}</div>'
            )

        # ไฮไลต์ชื่อ instruction ถ้ามี hazard
        has_hazard   = idx in hazard_indices
        name_bg      = "background:#fff3cd;border-left:3px solid #f0a500;padding-left:5px;" if has_hazard else ""
        hazard_label = " ⚠️" if has_hazard else ""

        rows_html += (
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<div style="width:210px;font-family:monospace;font-size:13px;color:#333;'
            f'font-weight:bold;padding-right:8px;{name_bg}">{instr}{hazard_label}</div>'
            f'{cells}</div>'
        )

    # header row — เลข cycle align กับ cell
    CELL_W = 52   # 48px width + 2px margin each side
    LABEL_W = 218 # instruction label width

    cycle_headers = f'<div style="width:{LABEL_W}px;flex-shrink:0;"></div>'
    for c in range(1, max_c + 1):
        is_current = (c == current)
        color  = "#6366f1" if is_current else "#bbb"
        weight = "800"     if is_current else "500"
        bg     = "background:#eef2ff;border-radius:6px;" if is_current else ""
        cycle_headers += (
            f'<div style="width:{CELL_W}px;flex-shrink:0;text-align:center;'
            f'font-size:11px;font-weight:{weight};color:{color};{bg}'
            f'padding:2px 0;box-sizing:border-box;">{c}</div>'
        )
    header_row = (
        f'<div style="display:flex;align-items:center;margin-bottom:2px;'
        f'overflow-x:auto;">{cycle_headers}</div>'
    )

    # ปรับ rows_html ให้ใช้ LABEL_W และ CELL_W เดียวกัน
    rows_html2 = ""
    for idx, instr in enumerate(instr_list):
        cells = ""
        for c in range(1, max_c + 1):
            stg = ""
            target = df[df["Cycle"] == c]
            if not target.empty:
                row = target.iloc[0]
                for s in STAGES:
                    if s in row and row[s] == instr:
                        stg = s
                        break
            is_cur  = (c == current)
            is_past = (c < current)
            bg      = STAGE_COLORS.get(stg, "#f0f0f0") if stg else "#f0f0f0"
            opacity = "1.0" if is_cur else ("0.45" if is_past else "0.07")
            border  = "2px solid #4338ca" if (is_cur and stg) else "1px solid #e5e7eb"
            shadow  = "box-shadow:0 0 6px rgba(99,102,241,0.3);" if (is_cur and stg) else ""
            label   = stg if (is_cur or is_past) else ""
            cells += (
                f'<div style="width:{CELL_W-4}px;height:36px;background:{bg};opacity:{opacity};'
                f'border:{border};margin:2px;flex-shrink:0;display:flex;justify-content:center;'
                f'align-items:center;font-size:11px;font-weight:700;border-radius:6px;{shadow}">'
                f'{label}</div>'
            )
        has_hazard   = idx in hazard_indices
        name_bg      = "background:#fff8e1;border-left:3px solid #f0a500;padding-left:6px;" if has_hazard else "padding-left:4px;"
        hazard_label = " ⚠️" if has_hazard else ""
        rows_html2 += (
            f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
            f'<div style="width:{LABEL_W}px;flex-shrink:0;font-family:monospace;font-size:12.5px;'
            f'color:#1f2937;font-weight:600;{name_bg}white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis;">{instr}{hazard_label}</div>'
            f'{cells}</div>'
        )

    return (
        f'<div style="background:#fafafa;padding:20px 20px 16px;border:1px solid #e5e7eb;'
        f'border-radius:14px;overflow-x:auto;">'
        f'<h4 style="color:#4338ca;margin:0 0 10px 0;font-size:15px;">⏱ Cycle: {current} / {max_c}</h4>'
        f'<hr style="margin-bottom:10px;border-color:#e5e7eb;">'
        f'{header_row}'
        f'{rows_html2}</div>'
    )

def generate_report(instructions, metrics_on, metrics_off, stalls_on, stalls_off):
    lines = [
        "=" * 52,
        "   🚀 RISC Pipeline Simulator — Performance Report",
        "=" * 52,
        f"\nInstructions ({len(instructions)} total):",
    ]
    for i, instr in enumerate(instructions, 1):
        lines.append(f"  {i}. {instr}")
    lines += [
        "\n── With Forwarding ──────────────────────────────",
        f"  Total Cycles : {metrics_on.get('cycles', '-')}",
        f"  CPI          : {round(metrics_on.get('cpi', 0), 4)}",
        f"  Stalls       : {stalls_on}",
        "\n── Without Forwarding ───────────────────────────",
        f"  Total Cycles : {metrics_off.get('cycles', '-')}",
        f"  CPI          : {round(metrics_off.get('cpi', 0), 4)}",
        f"  Stalls       : {stalls_off}",
        f"\n✅ Forwarding ลด stall ได้ {stalls_off - stalls_on} ครั้ง",
        "=" * 52,
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 0 20px 0;">
    <div style="display:inline-block;background:linear-gradient(135deg,#eef2ff,#e0e7ff);
                border:1px solid #c7d2fe;border-radius:20px;padding:5px 16px;
                font-size:12px;font-weight:700;color:#6366f1;letter-spacing:1px;
                text-transform:uppercase;margin-bottom:20px;">
        Computer Architecture Project
    </div>
    <div style="margin-bottom:16px;">
        <img src="data:image/png;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAIvBAADASIAAhEBAxEB/8QAHQAAAgEFAQEAAAAAAAAAAAAAAAEHAgQFBggDCf/EAG8QAAECBQEEBAUJDg4QBAYABwECAwAEBQYRIQcSMUEIE1FhFCJxgZEVMkKVobGz0dIWFxgjUlZicnSSk5Sy0yYzNDU2N0NEVHN1gsHhCSQlJ0VGU1VXY2RlosLi8IOjtMMoZnaEhaRH8ThItcTj/8QAGwEBAQADAQEBAAAAAAAAAAAAAAECAwQFBgf/xAA8EQACAgEDAgMFBgQFBQEBAQAAAQIDEQQSIRMxFEFRBSIyM2EVUnFygZEjNUJTJWKhscEGJDRD8EXR4f/aAAwDAQACEQMRAD8A69HCAQQRsOYIIOcEChz4QQe7BAgcYDBAIANDBjSDywQAQaQQRQGkEEEAAgxygggUIMQDvgiECDSCCADAzBBBABBBBFKEEEGsQB3weeCCBA1g5QCGIFDGRBwg58IOMDJLAcoIDAIFDWCGBmDgeUAAHOKhoIE8IcRsBBBAYgCCAQQAQeeCCACCDEMDugAgGkOETiACDMEHlMChB54IIAIfKFBABAYOcOAFBzgghgBDELMEXADiYe6YIM98AG6YN0wZgyYYAbpgwYMwZ74YAYPZBjEGYUAHOCCCGCjhQeWCIQIIIO6AHyg80KCACCCCADhBAIIACICIDDgQpghnhCMAEEEEAEHOCCACCCCAA8DFB4aGK4CIqYPPzweeKlDJ7opigIIIDAoK1gxpxg8kHOBGsgeyDzwcRCOkDAIIIIEDSCCCAF70GBDgilDGkEEEAEEEBiEDHOCDzQQADGYIIIoAwYgggUMQYHCCDyRCBBBBAAYIIDAC0h6eeCCBQg0g74UCBBz0hmFiBRiDHKAQGAEIcEEALuhwGCBAgggMAEEEGkAEEEEUoQQQQAQQQQAdsEEECBBBAIFCCCCACCCCIAEEEEAEAgEEUJDEB4we9BziGaQQQQQKEGMwAd0VgY5RMkENByirEGIIZAQawQRAEEEEAAgghiAEIYgggAgh+eFADhQZggUIIIB3YgAggggBweWFyggAOYIAIADmKUMwRUBDwIZBRDwTD9yGMwyQpxBumPCcqNPkx/bc9Ky/8a6lPvmMJO39ZMkSJq66M1j6qcR8cVJvsjFziu7Ni3YMGNJe2ubNm85vGlr/AItzf94RbK20bM0nHzUsHyMOn/ljLpz9GY9er7yN/wAGDBMaCjbRszVwuhgeVlwf8sXDW13Zq6Ri8aWj+NcKPfAh07PRjr1feRu26YMGNckr/sidIErdlGdJ+pnEfHGblKjT5zHgk/KzH8U6lXvGMWmu6M1OL7MuCMaQsERXx/8A5QRMlyUQRXjSER2QyUpgh47zBiAFmDWDAggAgggiEGIMQoIAcEHKEMd8CDhQ/PCgAI7MQoYgxACEEGIDABBBBABBBB54APLCIHZDggDyIMOKyAYoxjjGRchB3wZxBABCPdD5QoEDnBAYAIGLWAggg4GBAggg78QAQQQQIEEEEUoQQQQAcoIIIAIcKCBA5QQQRAHdCMOCBQhQQ/LAgCAcIUEAHA6QQc4BACghwjApVBBBAgQQQcoAIO+CCAFiHmDlABABBARBkwAQd0GdNIDnMAAggggAgggigIINYIAOcHKHAe4xAKAQ4M6QAtIIIIFCCDnDxALuEEEEDMIIIIADB54YioAc8wGQAxDggjEBrBBBABBBBAZCCHygxrAgQ+EHnggBQ4UEChB5oeIBAoocEEAKHBnvg17IAXOHgw93SDOkAIA9kPdHIRa1aqU6kyS52pz0vJSyPXOvuBCR5zEQ3d0ibTppWxQJScrjyTgOJT1LGft1akd6UkRshXOz4UarL66/iZNI00Bizq1WplJljMVSoSsk0NSt90IHuxyDdm3W/qyotIqMtRGHFBLbUg3hw92+vKlH7UJiwoWzPaJd0x4eihzy1r4zlWdLZPlU5lw+YR1LRYWbJYOKXtHc8VRydD1/bzs+pilNSs5N1d0fwKXJR+EVhJ8xMaDXeklUHMooNsMNZGjk8+VkfzEYz99Hpb/RrmXG0ruK5w2ojJbp7Od3u33OPl3REgUDYVs6peFPUt+qujiqoTCnQf5gwj/hh/2tfqyY1tvpE5/rW3DaFPq6ldyS1PUo+KiSl0NnyDe3lRjTLbUbqVkovKopVyUp9DavMSlEdl02jW/QWB4BTadTm0jGWmUN48+keM5dltypIerEpkexQvfPoGYeLivggHopP5lhyBIbEdoU6rfTaCWCTkmZeZQfyiYzsn0e9pDmN9ugSo7Fz6yR5ktH346JnNptqS58R+Ze+0lyPysRYHarTXDuydHqUx2YCf6CYvi732RPBadd5ENsdG+8VjL9eojJ7Eh1f9Ai5R0aLiIG9dtLT5JJw/8APEu/PDqjo+kWdUljvSr5MAvm5Fapsqb85X8mMfE6j1/2MvCaX0f+pEZ6M9wD1t3Uwn7hcH/PHg90bbsSPpVx0Z08t5t1HxxMZvi5gNbKm/MpfyYXzwKyj9Ps2ogc90LP/JDxOo9f9h4TS+j/ANSB53o87Rm89Uq3ZpPLE64knzKax7sYGobDdokl9MNptTChwMrMMrPvgx0r89OTaOJyh1KX7chP9OIvJXafaz5w45NMfbsb35OYy8VevIx8Fpn2Zyt4DtStYhYYvGnBI4NqfW2nzJKkRf0bbhtCp6yym5JeoLScKbnZZCyO47u6r3Y6yk7ytibwGa1KAnk4rcPoViLifpVv3AyfDafTak0RjLjSHR6dYPVJ/HAq0TXy7CA6D0k6i2Eor1sy7wA8Z2RfKCfIhecffRv9v7edn1UUlqbnJqkOkcJ1ghA/8ROUDzkR7V7YXs5qmVNUl2luHgunvqaA/mao9KY0C4OjY+lJXb1zBwjg3UGcE92+3w+9MTOls+gxrKv8yJ/pNWplWlhMUuoSs6yR69h0LHuReeeOKa3sw2jWlMGf9RJ1K2x+rKS8XFAdxbw57kXlrbdL+orgYVVJastNK3XGag3lwY5b6SlST5QfJEej3LNcslXtHa8WRwdlYEUkRC1p9Iq1p/cauGRnKK6rA61KTMMZ+2SN4DvKcRL9Gq1NrMiidpM/LTssv1rrDgWn0iOadc6/iR21312fCy6xrnWDlFXlhYHLMazaUwQemHiAFAIIcALyQ4NYMwIEEHKDlAgc4RhmFAohmD3YZGsLEAHlggggAggh8oAULA74qhQB5wRWQDFEZAIIOUHKBQEHKCCBBCCHyzCyYGLTDlBBBAxCAwQRShBBDiEFB7sMZg5wAtIIevbCigIIMwRAEEEEChBpDxCOYECCCCAD0wQHjmEeEAHPnC05w4UAOF5YcI6wKVQQQQAQcoIOUCAIDwgggAggzBnsgA58IXvw8wQAoIcKKUcHDnBCiAY0ggggA5wzxhQQIB8mYNOAEEEAEEEEUoQQQE6RAEOCCBkkEEHdCgUcA1IGISdSABHoBgwAYhwGCMQEEEEAEEEEAHmh4ELBhwIOAwofmgUUEBhiBcAIIM6QQAQeaFBzgA0h47oeIZ05QGBAYgyYx1x12kW7S3KnW6hLyEo3xceXgE9gHEnuGsc57SekZPTZXJWPLeAy3BVQm28vKHa22dEeVWT9iOMba6Z2v3UabtRCle8zoG8Lvty0ZHwy4KsxJII8RCiVOOdyUDKlHyCIFvzpFVKZKpazaciSZ5zk8jfcI+xbB3U+VRPkiNrMsG+9pM8qryrDz7cwrLtXqTqghY+xUcqWNdAkbvLIjoXZ/sGtKgFucrJXcFQGoMykCXQfsWuB8qiox1bKKPjeWcXU1Gp4gtqOe6RQL+2oT/qgwzUK4snAnppzdYR27q1eKB2hAPkiW7R6NbASh67q866viqWpviI8hcUN4+UBMTbWrhoVusBE7OMsFKcIYQMrxyAQOUakq9riuBZbtKhL6nOPCpgDHm1CR6T5IxlqrZrEVhGUNHTDmb3M2C2LJs+0Jfeo1FkZHdHjPlILh71OKyo+cx4VjaDatL3gqfEysabsuN/3fWj0xh02DVKytL12V9+Y1z1DCvFT5yMehMbPR7St6k7qpOlsdYng64N9fpVmOZ47yeTqUZYxBYNXTfVxVcfoctZ5aDwemM7vvgf8UeyaPtDqozUK3L01s/ubByofej/mMb7y4QwTEcsdkZqt/wBTyaC3swkH3OtqtZqM65zyoD3VZPuxmZKwrVlR4tKQ6RzeWpfvmMvR55ydEx1iEJ6p0oG72RfjWI5z82VVw7pFjK0akSuPB6ZJtY+pZSD70XwASMJAA7owc0yuqVh6VcfW2wwkeIg4Kj2w6T1spV3ab1ynmgjfTvHJTw092JjjuXKT7GbyIPKIIRiGQ4OELMKGCjOvECLSbpVLnB/bNPlHwea2Uq/oj3mNZdz7U+9GPtUf3Fb7N5XvwXCyThvGDHzlhWnNg71IaaPaypTfvGMK9sspTbvXUyqVGRd5ELBx5wAr3Y36LGszrkk2wptKVFx0IO92Rkpy8mYOuvu0acaJtApQzTa8zUG08ETB1P3wP5QjyXe9zUg4uG1nOrHF6XyB76h7sSIeMGBF3+qI62vhZqVH2h2tVN1PhxlHD7GZTuf8XrT6YuLosq0LvlwqtUSQqAUPFf3QHB3pcT4w8xi6q9p29Vt5U5S2C4eLiBuL9KcGNVd2e1OjuKftGvzEsTr1D6vFPnAx6UmKtucxeDBxk1iSyaBd3RtlilbtpV15hfFErUfpjfkDiRvDykK88RHV7av/AGZT5qT0vUKItJwZ+Tc3mF9m8tPikdgWB5I6dbvK5aAQ3dtCUpoaeFS2MHy67vujyRtdEuGh3A0USU208pScKYcG6vHPKTxHpEdMdVbBe9yjllo6ZvMHtZz3YnSLq8mUy1305upMcpqSSG3gNPXIJ3VeUFPkie7LvW2bwk/CbfqrM3gfTGjlDrfcpCsKHnEaRtA2EWjcSlzlJC6BPq1KpRILDh19e0dOPNO6e+Oeb42dXzs8mhVpmXcEvLKKmqtTHFbrY7VEYW3pxzp3mM9lF/wvazDqanTcTW5Hbx7YDrHLezXpF1WQLclekv6qSeBuz8qgB9I7VoHir56pwe4x0ha9xUS56Uip0GpS8/Kr032letPYocUnuODHJbROp+8jtp1Ndy918mSxzxBFXGEUjPGNRvEfJBmFCOeyLgDghQ4YAawQGHrEAQQocCCIheaKoWO+AFBBBAAYNYIIAPPCIz3Q4IA84IrIzFB4xkAghHOYMwwXA86QsQHjADyAgRrgIIQzDimDWAg74IcQBBp2QjnMBikDzQaQoYOkCh3wQCDnygA1zBAIIEHBCgiAfmhd+ICYIADAeGYR4QQKEEEB4wAoBDggAghQ8c4EHx4QQAaQQKEHkg5wRABgggikCCAQQAc4XOHx5QCACAwocALHnhweSAQAQQQRShBBBABBBBABBBpDiEFDxiAQQMohBB5oIGYQvPDhgEwAJwPLFfnhAQ8RGTIQcYPPBEAQQQQAQAd8GDzirhACHGCHBABC4w8wcO8wAYGYD2Yg588wopQg8sPBMMJPPEAIAHnDAwMQxwjG3JXKTbtHfq9bn2ZGSYGVuuHQdwHEk8gNTDvwiNpLLMlkRDm1rbnRrZW9SLcDNYrKNFq3iZaXP2ah65Q+pT5yMxD+2DbrV7rD9NoTjtFoBG6tRO5MzI+yUD4iT9SNe08oymyHYHVK+01U7t8IotKIBak28ImX0/Zf5JJHL132sdkNPGtb7n+h59mqna9lK/U0pti/NrV0EoExWp9Awpaj1ctKJP8AwtjuGVHvxE/bNOj/AG5QFNVG5Fpr1SGCG1pxKNK+xRxUe9We4CJMk5e27Kt5MvKtSlJpjHBCE7oz76lHzkxp0xdVx3dMLkrQlFSsmDhyde8Ujz6hPkGVeSJZqJ2LEOIlr0tdTzP3pG23JdNDtpkInH0h1KfElmRleOWnId5wI1EVW+LyOKPLii0tX75WTvqHcrif5o/nRm7Z2fUilr8LqBVVZ5R3lOPjKArtCTxPecmNx1xiObdGPbk69spfFwjTLe2dUKnL8Ing5VZsneUuZ1TnuTz8pyY3FCUoSEoSEpSMAAYAirWCMW2+5sjGMewAxYTFYp0u8WXHiVA4VupJxF8reKVbpwrBwe+NboU1T5SSel55IS+FHrAtGSqCQlLBsjS23mg60sLQoZChzirnGJtNDiaatagUtrcKmwezSMvjWI+Cp5WTCWuNJ77pVGaGhjD2sNZ/7pMZrEWT5JDsYW45YNtKqTDi2X0AAlJ9cCcR70OQQwwJkuKceeSFKWr04gub9Zn/AOb+UIvKb+t8v/Fp94RM+6EluPXd04wFPfFWsYuerCWZoysvLuTDqfXBHAQWX2Mm0u5kt3vg3e+LWl1FqeQrdSptxBwtCuIi9MTLXccPlHjMD6Q59qfejHWr+szf2yvfjJzH6Qv7U+9GNtT9Z29fZK9+C+Fk/qRkyIw106y8r90J94xm+cYa6v0iV0/fCfeMZR7kkuDLnjFLi0NNlxxQShIySeAEV48kYm6kOGl5QCUpWFOAdmv9OIi5K+Fk9Zas0598MoeIUThJUkgE+WL88eMa1W5mmTNObZk0JU8pQ6tKEYI7o2RsKDSAs5UEje8sVrBIvILAWkpVhQPEEcY1G4dn9DqRL8ohVNmgd5LkvonPenh5xgxuEEFJrsJRUu5GC6jfdmn+6TArlLR+7pyVpHl4j+cCO+Ntti7KFcrQRJzAS+oZVLu4C8eTgod4zGxGNQufZ/RauszUsDTp0HeDzAwCrtUn+kYPfGe6Mu/BqcZx+F5RpW0vYFbVyKdqFAUKDVFAkhpOZZ0/Zt8j3px35jnudp997JLpbed8Ios+vxW5hlW/LzaRrgHG6scfFUAoccCOoGLgueznEy90S5qFOzuonWtVDsyefkVg95jb3Bbt50Fxh1qTqtOfG6406jeGewpOoPoMb4amdfEuYnNZpa7eY+7Ii7ZNt5pVfUxSLtDFIqy8JQ+MiVfV2AkkoUfqVHHYTE0AgjI4Ry1tf2Az9Jadqlkh6pyA1cpzqt59pPPq1H9MSPqT43erhGtbHtt9astxulVnrqrQEKKC0rJmZQg4IQVHVKcEFtWo5EYwc56eFq30v9DGvVTpey5fqdlHUYzCI550jG2tcFGuiis1ehVBqdk3h4rjZ4HmlQ4pUOYOojK4jieU8M9BSTWUeeINIqI74R0MCi5cocKCIAEEBggQIIOUOAFiFFQhHtzAC74O+DSCACCCCADMUkE5wYqgi5B5HAPGDTtipQ1hRS5FDAgggAxC1h5gMDBiggggQDCOM84cEUCPcYPOYfngiZAQcoIIEDzQQcIIAIIIIAIPPB5oRilCCHBEIGIR46wYgMAB48IXOGeMIwAQQCHrAo4IIIEDXjBBAMwAQQQQKEEA7IOUQgQeeCCKAyYDmDMEAAghaQ4AIIIIAAIIfmg07IANYDw4wadkLTsgBnywcRCzygziBVEcBhc8w4GeAg80EPGYFARWMgwkpweEPzRGzEesBhadkGYgDhBAYIFCAQQxABjWHAO6CACGIXmghgiAcOMInSCDMUyDMGMmCKxAAOHfB6YXpiNNt21ql7Paf4KyG56vvo3paTzogcOsdI9ajPLieXMixg5vCMJ2RrjukZzahtDt+wKSmbqrqnpp4ESskzq6+ru7Ejmo6Dy4EckXPX722v3fLyxYVOTaipUlTJY4Zl08CrXTQEBTiu3TGcR5WpRLy2wXxMOh9U3NuEGeqMwPpMsjkMDsB8Vse5qY7C2cWLbuz2gKk6WjK1J3puemCOtfI9ktWgA7AMAR2+5pV6yPPXU1kueIGlbGdh1IsxTNZrSm6tX0jIXj6RKn/VJPFX2Z144wNI2+875kqG4afII8PqijupZRkhKjw3sc/sRr5IxNduyqXLPKoVmNq3MfTp05TgdoPsR38TyHOM/ZVmU222w9+qqgoePMrGozxCB7Ee6eZjlk3J7rOWdUIKK21cL1Nfo9lVOvziKxe8y44vi1JIVhKB2HHDyDXtJ4RIcqwxKsIYlmkMtNjCEISEpSO4R6ZEGdYwlJy7m6Fah2CDgdIACTFQBzqIxNmCnGYe6cRVgaQ4xyXBSARGDr7LSqvT95tB314VkcRkcYz0YSvHFXpn2598RY9zGa4M0kYTgaAaQHiIBwgPbEMsGGtj9/fdKozUYO2FpDk+3kbwmCSOeO2M4MRZdyQ7FhW5d2ZpjrLI3lqxgE45xcyaFNyjLahhSUAHygR7YgwMRM8YMtqzkBGttzbdNrE5vJLqFnO8jUp5492MlW55cs2liXG9MvaIA5d8elGkBIy2FeM8vxnFccnsjJcLk1y954RaURt1+oTFQU0Wm3BupSefDX3IzMGeyKXHEoQpa1BKQMkk6CMW8maW1FE2tKJZ1S1AJCDknyRjbVz6jtZHsle/FqtT9fmS22VNU5tXjK4FwiM8yhDTaW20hKUjAA5RXwsGK96WSuMLdWrEp90J94xmucYS6VDck285WXwQOZix7ia4M1ARkajIgEOMTMwNEYZTXKhutIHVkBGB63PZ2RnYwtFwa5VPth/TGb5RlLuYQXBSQcmEc8DCecaaALq0IB4FSsR5eGyXOaY+/ERZK8Ht5II8DOSZ4TTP34ilyfk22lOGZaISCThYJPki4ZjlHq+00+ytp5pDraxhSVgEKHYREdV+yKhR5xVZsiaXLPjVcmVeKsdic6H7VWnYRG0tT1bmWFTrDDCWBndQRkqAjLUyaTPySJgJCc6KHYRxjJNwMJRjZwahZl/S1WmPUqss+ptWSd1TSwUoWr7HPA/YnXszGu7ZdilGvkOVamLRSbgA/T0p+lTOmiXkjj9sPGHeNI3e8rNpVzS/8AbCOom0DDcyhI3h3H6pPd6MRrdHuOr2lPIot3IW7K8GJ4ZVkd59kP+Ic8jWM4yw91fDNUoZW23lepyzRKrfOx+9HmUINOqKQDMyMwStiabzgKODhQONFp1HDtEdc7KdpFB2g0xT1PWZefYA8LkXT9MZ7x9Ug8lDyHB0i72hWVbm0O3RI1VsLSRvyk6wR1rCiNFoVr6DkEaEGOP72tq7tkt5SzxmHJZ9CyqnVSWGG3xjVODnBwPGbVy11GsdScNUueJHK1ZpHlcwO6zCMRTsJ2wU7aBKCmVDqpG5JdveelhoiYSOLrWeI7U6lOewgmVT5Y4pwcHhnoVzjZHcikwoqOohEGIZihiFD74gCCDzQacxAjHwhHhAcdkECFPPjBmHC74FCCCCACCAaQQAiIpOkVmERnXEVEKIID3iDIilCCF54PPAYCCHyhaQMWgxDxB5oXmgYj88HbrASOyERAATBnlCzBAYHBAIOEAHuQQQQAQc4B3iDSADugzC5/1wQAGA5g96AwAQQQQKKHrBBAg4IBBACgh4ggUIIIIECA+WCFAD1ghacoIFHyhYhwaQAoflgHfC5c4AY4QeeCCBAzBBAIpQgg88EALWHByg5QNiCHB3QRAEVI4wgIYEH2IVQQocYgWNYesAMBgAgxkQQwIAIcGsEAEKCHw1gMCziDlC584NO0xkZDPkgA7oANYrAAiZJkWMHhD4QGI4257UJLZ7QghjqpmvTiSJKWVqAObqwPYD3ToIsYubwjGc4wjukWO3za1K2FT/UymFmauSZb3mGV5KJdB0613HLQ7qeKiOwEjmTZxYd0bWLumnnJ2YLRd36rWHsKUhRA8UZ0U4RjCcYSMaAYButm1l3HtavOZU7OTBQpzrqtV3ACpBI0CcjBcIxupxhIGowAD2ZSKbbliWk3JSTLVPpUkjyknmSeKlKPPiSY7ZSjpo7I8yPPhCWrlvnxFFnblFtzZ9aaafTm2qfTJRJUtaz4yjzWtXFSiefEmNPcm63tKn1S0n1lOt1peHHCPGdI7RzP2PAcTk6RUiSqe0uqCZmy9I27Lr+loScKcUPfV2ngngNcmJLkJOWp8m1JybKGGGkhKEIGAkRyuW3l8s61By4XETyodJkKLT0SVOYDTadSeKlntUeZi+80YY1iZCyn1JmcA44H4oYq8yf8FTHu/FGGH3NylHsjMeaDB7IxIq0z/mqY934ofqtM/wCapg+Y/FEwy7kZdMVRh/VeYGppUx6D8UXlNqDE+0VtEpUPXIPERjtZkpJ8F5BBBEKEY6uSC5xpDjCy3MMnebOfcjIwoqeCNZ4MbRqmJrel5hPVTbei0HTPeIyR1EYys0oTRTMSyi1NN6pUNM9xiukVHwoGXfT1c0369B0z3iD55RE2uGW9WpryZj1Rp3iTKfXJ5OD4/fi8pFRZn2N5PiuJ0Wg8Un4oveUYerU51D/qjTvFmE+uRycHxwznhhrbyjMwjziypNRZn2d5PiOJ0W2eKTF6Yj4Mk8mEmdbwls64lyffjN8sxhH/ANmMt9zH3zGbjKXkYw8wjBVbrJ6st0srLbO51q8cVd0Z2MIofoxH3L/TCImZhhpDLSWmkBKEjAA4CK4BwizqtQZp7HWOaqOiEDioxj3Mm0kKrVBmQlytZ3lnRCM6k/FFnSac87MeqVR1fPrG8aIHkgpUg88/6o1EZfV6xHJA5aRmRppFzjhGKW7lhwjF1uqCTSGWE9bNOaIQNfOYqrVTEmlLLCetmnNEIGvnMUUWlmWUqbm1dbOOaqUdd3uEVLHLJJtvCHQae7JtuPTS9+ZfO84c6Dui6qc+xISxeeV3JSOKjBU51iQli88ruSkcVHsEYumyD09Mip1Ia8WmeSRyJEO/LHbhBJ092prM7VEnCh9LZBICR2xd+oVL/go++MZIcIfKDkyqCMb6h0z+Cj74xS5QaapCkpl90kEAhR074ykKG5+o2x9DXmG65KSxkG2G3EahDoI0B88ZWjyfgEgiXKt5WSpRHDJi8OIR4RHJsKKQvPFnV6dJVWQXJVCXS+yvik8QeRB5HvEXRODGLqdTW08mTkkB6aUfWkaJ8sVJ+RG0u5Hy3q1s1nwFdbUrbeXx9m0T7gV3cFdxjcK1Tba2g2k5JTzLVSpc4nI1wpKhwUk8ULB56EGNgmZVmblVsTbKHW3EbriFDKVDmPJEZTlLqezmqKqVL6yboL6h17K1ZKD39h7FeY8jG1NT+jNDi4fWJzJtS2d3JsquaWmGZyZXJ9cFUurtEJc3wCd1WNEugA5GN1Q84HSPR+2vS99yQotaLMtcss3vONoG6iaQMDrWwfKN5PEeQgxIM3KW7fNpuys0y3UKXOo3XG1jBB99KgfODHGu1Owq9squyWWxOzYlesDtJq7ZCXCpI9arAwHQM5GMKGdMZA64SjqY7J8SRyyhLTS3w5izuaAxGWwXalK7QaJ4NPdTLXDJoHhcujRLo4dc2D7E8xrunTsJk6OGUXB4Z3wnGyO6JQYXKKzrFBiGQc4IPPCi4LgcEGecEYkCEdBDggQWIIfHzQoAIM8oIOcAEEBxC484ApXxGBFPdFahmKSMRkiihiCCACDEELTjAjCDMIQ4phgBB5oIIAMd0Hmgg8kAEPywoD5IECDnBBEAQQofKBRQQQcIAIIIIEA8YOMEGIgFmCCHFKOA6wzCgBcIcB8sKBBwQofKAFBByhwAocBEHLEAA92CHC88AHGCAmCACD34IMQAhDgggUIBD88GIFiwgggMDIBBAIBrAFSeyKopTFURgUODGYcQCgAh69sA8sAAHYYZggzAgQjDhQKOFmGYIpRQAQ0+iKgMRBkAMQGHFlXapIUSjzdWqkymWkpRouvuqOiUgawIzW9rF+0nZ7azlaqJ6x1R6qTlUnx5h0gkJHYNCSeQBjjO3afd+2PaSttyYD9TnMPT04UHqZNkaZAzokcEIzknP2Ri52hXHcW13aI09Kybrj0wrwWkU7fx1SDr4x4BRxvLVyxjUJEdb7HtndP2bWgilsuCYnXT11QnVAAvOnjjsQkaJHIDXJyT38aaH+Znnc6qX+VGZtKh29s9s1umSCUylOk0FbrrnrnFeycWeaifijUJZFQ2l13wiYDspbkm54iM7qnVD/mPM+xGg1JMWtSmpzaRcopVPdW1b8moKefTp1iu0Z4k+xHlV2RKtMk5aQkWZOTZSyw0ndQhPACOWT2cvuzrjizhfCj2lWWZaXbl5dpDTLad1CEDASByEVkaxZVGnCdcQszL7W6CMNqwDFr6gpH7/m/vo08ep0NvyRlgmKgMRiBQk/w+b+/g9Qk/w+c+/i8epPe9DMQRhjQk/wCcJz74R4zFCeSgql6lNBwet3laZ80TC9RukvIz+kYWrU99p/1Rpow8n17fJYiqh1B11Zk55PVzbfEEevHaIzEOYscTRZUmoNT8vvo8VadFoPFJ+KL3XsjDVeQeZmPVKmjdfT+mIA0WPJF9SagzUJbrG9FJ0WgnVJg15osX5MuwNMQ+EEEQzCMZWaaZndmJZXVTTeqFDTPcYycEE8EayY2jVLwsKZfT1U03otB98RkSYwkxui8JfGAVMHPfxjNY74rRjF+pgKs2JW4JGYl8oU+vdcxwUNI2ARhLgH91aX/Gn+iM2IS7IkO7MI9+zCX+5j75jORg3v2Xy/3MffMZyEvIsPMIwh/Zh/8Aa/0xm4wpP6L/AP7X+mERPyMzwjXpBtM5ck66/lwy5AbB4DzRsXKMFQx/d2q4Ps0/0wXZkmstGcjGVqp+BJSyynrZlz1iBr5zGTI0jBI3Td7u8ASmWBBPLhCP1LNvBc0SmKl8zU2rrZxzVSic7vcIu6jOMyMsX3j3JSOKj2RcJ1jBzLaZi62m3RvobY30pPAHPHEO75D91YQqbIvz8yKnUx/Es8gO0iM8IBDg3ksVhBHjNTDEs31j7qW0ZxkxTPzbMlLqffVhI4DmT2CMPISz1WmBUKgnDI/SWeWO0/8AesEvNklLyRferNL/AIYj0GD1Zpn8LR6D8Ue/qbIfwNj7wQepsh/A2PvBD3Se+eHqxTP4Wn0H4oXqxTM/qtPoPxR7+psh/A2PwYg9TZD+Bs/eCGYj3zHT9W60CXpf059zQEDRI88XdHpiJBoqUetmF6uOHn3Dui7YlpdgkssNtk8SlIEe3ODlxhFUecsoMUvNtvtLZeQlxtYKVJUMhQ7DHoe2FrmIVkW1CWn9nNb9UqeHZigzSwl5knJQeQ8vYefA8jG4XFSbdv8As5ynzyET1Mnm95K06KQeS0n2K0ngeRjOTssxOSjsrNtIeYdSUrQoZCgeURY1MTWzS4vBphbr9uTyiUrPjFtXb9sOfaNeIMbotz7d0c8v4fD+FnMF40a6tj20VpLE4pmeliX6bPhH0uaa4HI4EexWj3spMdhbH9oNM2iWm3V5IBibaPVT0oT4zDoAyO9JGCDzB7cx5bWbFpO0qzl0qacDbow/ITrYCiw7jRQ7UkHBHMExx/ZFbunY7tJddm5FxE3KnwaqSAc8WZaJB8U6BR9khR7SNMqjrWNTD/MjkWdLP/KzviGdYx9u1inXBQ5OtUmYTMyU22HWXE8we3sI4EciIyGI4HweinlZKIIrIzwinWLkZFDHGDXtgAOIhAg0gyYIEEYIIIFEIBxgMGIAOMEPWDXjmAFjvhLirzxSrUQQRRBAePGCMgGsB8kGIIFKToYcBGYY7YGEheeHpBrAOMDHItOyCHBnvgBcIOMBx2wQAHjBBBABrBBDgBQjFXOEfRABChwoAOMAgggA8sEEECj8gggggQUOCCBQgg7oIEFDhCGIAOOkHmgggA80HOCCBQggggAgggiEH5oPNCg1gBga8IIpTzhjyRTNRHCg4wc4pkGpj0SIoA1zFaNYjDGIOcEHKMSDPkheaCCAA+SGNIQ7oqgBQCDnBABAIfLEAgURgxB54ae2AKkw4UUnMCYKgRzjkjpVbTUV+ruWlSppHqLSnN6edCtH5hGcpJ4FDfuq7N2Ja6Te0ddjWaJSlPhFdq2WZXXVlv8AdHsdwIA+yUIgXos7PvmvuwVaoywXb1EWkqSrBExMgAoaIPEJBC1fzRrkx2aeCgurLyOLUzlNqqP6k1dFvZebZpAu+vSwTXKi1hhtYyZSXVghPctWAVdmg5a7ZtFrM1WamiyqCQp97SccB0QniUk9mMFXmHExmtod1ot2jfSVJVUJkluWRjODzWR2D3SQI89mdrmg0xU3PArqk54761nKkg67ueZ5k8yfJGiU3J9SR0RgopVQ7eZl7boMlb9Kap8kPFTqtZ9c4s8VHv8AehViozEvMMyck0lyYe1G9wA7YzEYqtSUy5MsT8jul9nTcVwUI1J5eWbZRwsRPGXqc3KTaJarpbSlwZQ6jh54yHqlT/4Yx9+IxCJGoVOfbeqjKGmGgcNA53vLqYyPqNTMayiPSYrwSO7yPU1OnD9+S/34gFUpx/fjH34jy9RKWf3m37sMUOlD95o9JjH3TL3y6lZqXmc9Q8h3HHdVnEXHnjCT1JMsUzlJHVvN8WwdFjsi7pFTaqLBUkbjqNHGzxSfig15oyUvJirFOTOoDjaurmW/0twHGO6POh1B2ZK5aaRuTTOixyUO2MoIwkmP0XTneyk/kxVyjGXDTRnOUYSqyD0tMGpUwAPD9Mb5ODnpGbgjFMyayWtLnW5+UTMNgjOiknkeyLqLGsVCn0SkTNTqEyxJSMq2p595w7qG0jUkxxnte6Sl1XLUHKRYypii0hag0y+20TUJtRPsePVg8kpG/wA8g6DZXU7OxhOxQXJ2hOVCRkyBNzkvLk8OtdSjPpMW/q9RD/hinfjKPjjgiU2I7TrmR4dUKWw2tZ3usrdRy8vvOjivvsGPU9Gy/R+97S/HF/mI1zt0kHiVqyZRjqJLKrZ3j6t0PO96rU7Pb4Sj44qFcov+eKf+Mo+OODB0br8/g9pfji/zEH0N9+/we0fxxf5iMfEaL+8jLp6j+2zvL1bopwTVqcSOH9sI+OH6uUX/ADvT/wAZR8ccGfQ3X5/B7R/HF/mIR6N1+fwe0vxxf5iJ4nRf3kTp6j+2zvI1uh7296rU7Pb4Sj44fq7Rf870/wDGUfHHBn0N1+/wa0vxxf5iD6G6/ePg1pfji/zMPE6L+8h09R/bZ3n6u0X/ADvT/wAZR8cL1boec+q1Oz2+Eo+OODPobr8/g9p/ji/zEH0N1+fwe0vxxf5iHidF/eQ6ep/ts709XKL/AJ3p/wCMo+OAVuiAkirU4E8T4Sj444M+huvz+D2l+OL/ADEH0N9+/wAGtL8cX+Zi+I0X95F6eo/ts709XKL/AJ4p/wCMo+OKfVmib296rU7P3Qj444O+hvv3+D2l+OL/ADEH0N9+8pe0vxxf5iJ4nRf3kTp6j+2zvI12iDT1Yp/4yj449pOo06cc3ZSdlJheODbqVH3DHA30Nt+n972l+OL/ADMeM1sN2kW+34bJ0qSmHE671HqAS8nvG8Gz96SYyjdo5PCtRjKOojy62fQuPCemmZOWXMPqwhPpPdHDey/pGXxZdSRSrpM9XaUyrq5hidSoVCW0HrVrwokcd1zJOfXcI7Ptit0a7rclK3R5lqfpk62HGnANFDsIOoIOhB1BEbZ1OHPdEjap8LueMlLu1mZE9PJIlx+lNHge/wD74xsAAGgECUgDGIZjBvJnGOBwlEJBKjgARStQSkqUQAOJJjX3Zl6uzSpaVJRIoP010cV9wglkSlgy5qUgP34x9+IRqdP/AIYx9+I8nKXSZdgrdlmwhI1UrJjFStJYqM14QJcS8on1qRxXFUYmDczNeqlO/hjH34gFSp+f1Yx9+I8zRaZ/A2/dh+o1M/gaPdie6X3z1FRp+P1Wx9+IsZiozU1Nql6UGlBAyp1Wo80e5o9NHCUR6TGMfkqjTZ9b9KYbdYcSAponG6e7WMopEk5F5Sqm89NPSM60lEw0Mnd4KH/ZEO4qPJV2lu06eQVNODQjihQ4KHeI8qLITYnHqhPhKX3RgISdEj/sCMyBgiDeHwIx3RxIjTZ/PTts1pVmV5eUb39ovngQeCftTrjsOR2Rhuk3sx+ayg/NHRJUKuCmt4KE6Km5cZJb71DJUnvyPZRIG0S2U3FRvpACahL5XLrzjPaknkD7hAMeGzW5lV2lrlZ4lNUk/EfSoYKgNArHbpgjtHkjYpuL6ke5qlXFp1S7Psc0dFnaam2q83bdSmUmgVdwFhxSvFl5hWN0jkEL4H7LB5mOwuccbdK3Z0i17iVcVOlk+oNacKX20p8ViZUCVJwOCVjKh373aImTou7SnL0tNVHrEyHK7SUhDqjxmGODbvl9irvGdARHRqIxmlbDz7nNpputuqfl2JlhK4QQeaOI7yg444gzDUNYUUBzghHyQ4BjEKHCiEAiF5oZ4cYRgA0xwg0ggxABBC1xwh9pxAFKhpFMVK4CKYyKAggggAhHSHnnCOuNYGEkGnZBBC5xSDhQQ4AUOAQogKoNIp5wxAgzjkIBw4QswQAQGA6wjAAYIOXCAwAQQQaRAEEEKKgVQQQQKEEEECBB5YIIADBBBABBBBAoCCAw4AUGIfngiEyKCAwRShAdIIRGsAPAzxg9MOCBsFB5IemIBADTw5RUnhAkQ4jZAgggiAIBAYBmAHjvhwQcOMAEEEBgAMKCDHOBQGvOK044ZilIPmiqKMj88WtTnJWnU+Yn519LErLtqdecVwQlIyT6IudBxjnfpi30mXkJWwKe+Q/OJTNVLcJyGAo7jZP2akkkfUpIOh1yrrdklFGu2xVQcmQRedWr+1/af4TISijO1RxMrTJVw4DDIyUBfYACpa8Z1KsZ0jtOy7Zo2zqw5ajyq+rkqeyVvvrACnF+uW6rHFSjkxEXQ4sJDEhM7QagwevmwqVpm+PWsAjfcA+zUMA/UpGNFayLtQnZiuViTsmlrw4+pLk2sDISkagHyDxiPte2OnUTUpdOPZHLRBxh1Jd2YiwpWbvO8X7xqbSkSMsrq5FlfAEcPvc5P2R7ol1J0iypdOlqTS2KfINhDLCAhA5+U95OpjHpfuQfvOU8yv8Aqjlk97OquPTXPcz0PlGEExcXOSlfvv8AqioTFwfwOV++/wCqMdpt3/QzHOHGH6+4eUnK/ff1wuvuH+Byv339cTaN30MupSUg7xwAM5i2ZqUg871TU00tfIA8YwlberCpBSZtlpplRAUps5Pvx5VuXpLdMQ5JqQHgUlsoV4x8sZKCMHY/I2saxgbiljJLFYlD1byCA4OSwe2MzJl0yrReGHCgb3lxrGPuz9Y3/Kn3xGKfODOSzHJk2F9YyhzGN5IVjyiMPJ/svnP4hP8AyxlZH9RMfxafejEyf7L5z+IT/wAsWPmSXkZuBWkEEYGw486c20R56tymz6VeKJCSaRP1MjOHXTktNntCQN8jtKDyjN7FrFo2zy0vmvuZKE1p9gOOuLTvGSbVjDLYHsjpvEaqJxwERDeEu3d3SjnWZ0b7Uzc4ZcQdQUMqCd3B5ENYI7zEx9IGdmEMUmnhR6t1bj6x2lOAM/fGMdYp221aKLwpcv8AA54Wxpqs1bWXHhfiY2ubV65MzSvUeXlZGVGietb61095Od0eQDzxjhtOvDh4bLfiqY0tCu0xWT3x9BV7F0MI4VaPlLPbGtsk5Oxm4nadd/HwyW/FUx5J2o3etO83UJVQ4Epl0GNQWfFwIjuuS03LXgGJB5Uu5Out9UoO9WnecUE+MeAG9xJ0HGJb7N0UFnpL9jZptbrLpOPVeSdRtOvHOs9LfiqYPnm3h/DZb8WTEXXDTtp9lIK7qtOoy0ugEredl99tIHEl1oqQkd5MeNLvKlzSAXi4zn2Q+mJ9KfijCvRez59q1+xtts9pV95v9yWPnm3ef37LfiqYfzzLvx+rZf8AFUxpMnMS02gLlphl4fYKBj2zjnrHQvZGhf8A61+xxP2nrU8Oxm4/PLvDP6tl/wAVTB88u7/4bL/iyY04rzBnewAcw+yNF/aX7D7V1v8Acf7m4HaZd+P1dL/iyYR2m3hynZb8WTGmzK22EdY+8hpPatQT78YCo3XSZUkIecmCP8kg49JwI1y9l6GPetfsbIa/Xz4U2Sgdpl48p2X/ABZMVJ2lXkrUTkv+KpiH6RcVw3JOGTtWgzFRcBAPg7C5gpzw3t3xU/zjBetNva35qXkrtlZumTU00X2ZRbze+Ub26CUtqO6CQQN7jg9kalofZ7eFWv2Ozqe0Ut0rGv1Je+efeHKdlT/9qkxdUravcrM0k1GXk5+WJ8ZCWuqcx9ioHGfKPRGg0+URIyDMqnGWkAKParmfTmPbewI2z9iaGccOtHJH2xrK55jY+CW9pVhUPapaCK/QtwVppBMo/uhKnSnOZZ7TOMnTmlWCMjIOn9Cy/HKNeqrKmXSml1tK3pZDhILM2kAkAHhvoSrI7UDtMbL0fqo8KjVqZvHqltImQOxQUEk+cEeiIcutSrZ6S65injqEy9yyr6AjTR1bSnB5+scHnjwNJB6e+3Qt5SWUfUu5aimvVpYb4Z9CcgnQw+cAGkOKdJgriLszPStKS4W2nwVOKHEgcoy0pLMScsGmUBDaB/2YxdR/ZRT/ALRX9MZh/RhZ+xMZvska13bMEwXq5NdasFuQbPijmsxnk7qUhKQAAMAAcIxNpa0Rv7ZXvxkZkOdSvqvX7p3R340iPvgse2TxmKnIMPdU9NNIXzBPCLlK0qSClW8DwIjVaHK0x2mrXPlBfKldapw+MPJHtQVVZuQCZRlt1gKO4pw4OOzjGTgYRseeUbNgZgwIxBfuAcJOW++/6oOvuD+BSv33/VGO0z3GXhc4xHhFw/wOV++/6oRmLh/gUr99/wBUNpHMzBOIi3aPLTdsXFL3rSmyWysNzzSdArOmf5wwPtgkxu637iP7ylfv/wCuL6dkWajIuyc60lxl9BQ4g8CCNYyjLYzCa6i4MFcNIot/WTMUycHhFNqcv4qwNU80rHYpJwR2ERxPR3rj2PbUuveZ6ypUd4szLaRhM2wrBUE68Fp3VJ10UBngY642cPTFs3JN2TUnCpsqLsi4r2WdcfzgCfKFRpfTAsIVGhs31TmAZymIDVQ3QMrlckhZ7S2o5+1UqOrTzUJ7H2ZyX1ucOou6JvoVSkazR5Sr018Pyc4yl5lxPBSVDIMXsc3dDi+Rib2fVB5W+gLnaaVcNzI61oHuUrfA7FKx62Okcxotrdc3FnVTYrIKSFjvikiPQRSoaxrybCnHphwoYgAEEKCBMBAYIfCAKYIMaZggA4mCDQGCAErhFJ4RXp2wERUweXlhiA8YNeIilFmAw4IoKQdOJggEB44zEya3wEPzwtIIEGBCgMBgA5woIcChAcdsPMBgBZ0gEGkGkAEEPgIUQgHj3QofOFFKEPhByhcoIFUEHGCBA88EEEQBBAYIoAQQcoNIAIcKCIBnTnB54XmggMDz3woIIoCCCGIgFCAzFUJOhimURwQGCBkEMQjiGmAKx5cwQQRiwEEEHKADHdFQBAhDyQ/NAgHMHnggPkEBgMnhAeHHWEIPPFwVIIIBDTxiFKhoBAYcGOyBDHXBVJOiUadq9ReDMnJsKfeWeSEjJ96OBaf80O17askOKWxP16aKnN058DYA1x/FtjA5FWO2OiemjdCpS15CzJJThmKo4JibDaVEiXbOQkkcN5e6MHiEqHbGM6F9i+CU6oX7PS60zE2VSUh1icEMJUOsWARkbyxjvCB269lOKqnZ5s4rk7bVX5Inqam6XZ9oZaZSxI06XS2wynTQAJQgd5OB541/ZDTH3ZaZuqpePPVJRKFEcG86kdgJGncExhNp65i5rrpllShcSyFCYnHEA4ToefDITk+VSYk+RablZZuXYQlDTaQhCBwCQMARzNYj9WdMW5T+iKnJyUQsoXMtJUDqCoZEUGfkR++2fvxCXTZB1alrlkFSjkntML1Jp38FR7sa+Dc8lRn5H+FsffiD1Qkf4Yx9+IpFJp38EbhepFNP70b92GIj3iv1RkB++2fvxDTUZAnAnGMn7MR5mjUw/vRHux5uUOmLQpIlggkeuSTkQxEe+ZFaEOIKFpCknQgjIMWUvR6ew+HkMDeGoySQPMYtKa7NyE0mnzSVOtq/SXQM6dh/70jNQ7BYl3CMTdx/uE/5U/lCMrkRjLnaceozyGUKWslOEpGTxERdyy7F9I/qJn+LT70YmT/ZfOfxCf8AljLSaSmUZSoEENpBHZpGKk/2XTn8Sn/ljJeZH5GbhHhDgMYGZ8/qcAnpVOAcPmrmj6XXDEsdIUgz1F/iXvykREcmr/4qncfXXM/CORKnSGcxUaJgcWXvykRlJ/4tR+VnnXLPsu78URiTg6GLyh0+o1uqN0ykyxmZtwKUlvfSnISMnVRA4d8W9LlnKjVJSntFKXJp9thClcAVqCQT3axNuzzZVV7Yu1itTdSk3mmmnEFDbawSVJwNTpH0mp1MaI9+T4+MMkLVOUm6ZUX6bUGSxNy69x1sqCt04B4pJB0I4RqO0OnNzdKRMEHKSWlkckrHH0+/HRl5bJKxXLtqFYl6pJtNTjwWlC2lkp8VKdSNOUQdU20vy03ILAKiFN5+yBwD6RFqvhqK+/JnS5VWpo7J2XXgu7NllvXM2ULXNyyUTSTruvIyhwE9oWlQjFXds02ZXcVrrtnyTc0vjNyQ8He459e3uq4+mIm6EF0pm7fuSyXnMOy7oqUq2dMIXhLgHkWkE/xg7YnMTAVHkKrEml5H0Oo1U62mvMgi5uizJqSXbKvd4Og5SxVmkqPkDjQSR5d0+eITuun3rs3upqgXi0lO+2HULQ71zbrRJTvtr0JwRqFAEaZGoz3GcK5Rq213ZlRdqlCkpWfn3aZVacpZkpxCEq0UMFCwfXIOEkgEHKQc8o3xtsray8o0RlXqMxlFJnMyMrQFoIUkjIIOhHbGBlZW77svlNo2ikOTi0FQR1qWhhIBWpS1cAMjhr2Axkrzta+tks6mTr1PTM05xzclZpolyXfJOgSoaoWfqFa8cZ4xLHRHsa4qZdNbvy5aLN0wOyPg8h4Snq1OFxwLcO4TvJA6tsDIHEiOu/UJ15g+TRptG67X1FwW1tdFaffSH72vhmXcUAVNU1vrVg8/prvH7wRJ9sbEdkVspQpFvKr02jB8Jqy/CCVD2W6QEJP2qRG3hW6eOsMO6xwyjOfxSOjxm3iEUjLUhaWnGpKnycrJSyODbDQSkDsAGAPRHD+1evovrb/WKq04HpKTe8Gl1DOC1L5SPMXCs6cc5jrPaZdSbK2U3HdAUBMMy/UygOfGfcIQ2NPs1J15YzyjirZ3IJlaYt8eyIaQTzSj+v3o2aSpOxv0GoulHTZk+WbZvQKOkUAwEx7TPnkiRdgOPmsnx/u8/CoiLdsasdIGeI4irSJ9xmJR2An9Fs9gf4PPwqIivbNp0gKhp/hWS95mPj3/ADiz8qPs9L/Kq/zH0PEEA4QRieiYWo/sop/2iv6Yy0z+kOfan3oxFR/ZRIfxaveMZd8EtLAGTumM35GCXcxdoZ9RG8j2SvfjMRirXadZo7aHm1Nr3lEpUMHjGVEYvuWHEUWT9KkH3i65Lp3zqcEjPlxF2hCW0BKEhKQMAAYAiqMNVJibm5o06TbWhP7q8QQAO6Lyw8R5L5dRkUKKVTbII45WIQqUgf34z9+I8WqJTUtpSqXDhAwVKJyYq9RqX/BEe7DETH3z19UJDH6sZ+/EL1Rkf4Wz9+I8xR6bylEe7D9SKb/BUe7DER75X6oSB/fbP34itE7JrUEomWiScABQ1jw9SKbw8FR7sVtU2QaWlaJVAUk5BhwVbvM1TazRnH6azX5Alqfpig4FpGu4Dk+XB18me2M5RKnI3PayJhxpDjM00pqYZVqAfWrQfdjLPgONqQtIUlQIUkjQjmIi2xetta/KhabocMlM/TpNZBIzjI170gjyo74zXvR+qNU3snx2Zyfd0lWtkW1hcrTXVKmaNMImact1X6ewrO4FnmFJ3m1HtCjpHd1p1yRuS26fXaa5vyk8wl5o88KGcHvHDzRBvTKswVK2JO8pOXLk3SlhmaKE5UqWWeOBqd1ZB7gVHti16FV1b8jUrGnFLS5LqVPyKVgj6WogOpGexZCv/EjqtfWqVnmjjp/hXOHkzpIcNYDwgI7RCMcZ34KdQIOUCuMUxcFHAIIcQMUPEGe6DzQII8IPPDGIXmgQOMKAQcoAIIIIFPMg5PGFHorhFEZAIIIIAR0gJ5ZgVyGIDiBhJCyYIUECYHyhQQQAQ4BB5ogHBCxBFAeSHCg5RAEHKDzwRQEEKHAoocKCBCrXsxBBBAoQQQRCBBBAIAIIIDwigO6CCFAoQQ4IAIIIPNABBmCLSp1KQpkqqaqE5LyjCfXOPOBCR5ycQwQu4BxjQX9s+ydl0tubQ7c3hx3Z1Kh6U5EUjbZskP8A/EGgH/7n+qMlCXoVNIkGFGgDbVslI/bCoH4zB8+nZL/pCoP4zF2S9DPdH1N/4xWjyRHo21bJMj++FQPxmKvn2bJAf2wqB+Mwdc/RjciQRx80OI9G23ZJx+eDQPxmD592yP8A0hUD8ZEY9OfoTKJC58YOUR78+7ZH/pDt/wDGhAdt2yP/AEh0DH3SIdOfoMokPHODnEefPv2R5/bBoX4f+qD59+yP/SFQvxj+qL05+gyiQ+ekHm1iPPn37Iv9IVB/GP6oEbb9kS1BI2h0EE81TOB6TpE6c/QuUSJjT3YUWVDrVHrsmmbotUk6jLqGQ5KvpcSR5UmL8jEYlRSIrAxCTxhnQcIgDOsUTEzLSrKn5l9phpPFxxQSkecxGm3ra3Stl1voedbTPVmcBFPkAvHWEcVrPsW05GTzzgamOOz89LbtXnn3Vv1ZttQQ51rvUU6T0yEhJJSDwOAFr1GdMRsjXlbpPCNNl6rO4JzaxstlphbE3tAtdp5BwpC6k0FJPYRvR4fPh2ShOBtGtUDuqbXxxzDJdGWu9UkzN5U1pWNUNSDiwn+cVjPoEXY6MtRPG9pT2tX+cjHq6T75yv2lH0Ojjtg2Sg5+eLa+f5Sb+OKhtk2Tc9o1r+2TfxxzeejFUD/jtJ+1q/zkI9GGofXrJ+1yvzkOrpPvk+0Y+h0kNsuyYf8A8RrX9sm/jir582yb/SNa/tk38cc1/Qw1H69pP2tV+chfQwVL69ZP2uV+cjHq6T74+0o+h0qNs+yX/SNa/tk38cP58+yb/SNa/tk18cc0nowVLlesn7XK/OQfQw1Hh82sn7XK/OQ62k++PtJeh0t8+fZN/pGtf2ya+OF8+fZNjTaNa/tk38cc1fQw1H69ZP2tV+cg+hgqP17Sftar85DraP75ftKPodKnbNsn/wBI1r+2TfxwHbNsn/0jWv7ZNfHHNf0MFR53vJ+1i/zkP6GCo/XtJ+1q/wA5Dq6P74+0l6HSQ2y7J8/tjWv7ZN/HHojbHsoUcDaNa2f5Ta+VHNJ6MNRHC9pL2tX+cig9GWrDO7e0j56av85DraP+4PtKPodg0K4aDXmA/RKzT6k0oZCpWYS4CO3QxeIlWEzq5xKcOrTuqOeI/wCxHz/u7Y5tBsd5VZpYM+0yN4z9EeW1MtAa5KAQ4P5hV34iV+jl0jpueqUpal/zbTypkpbp9YOE76zgJbexplR4LGAScEZwTs6cZx3VSyjop1cbDq/MHKKEEka6RUI0s7D59SIJ6VLn/wBVzPwjkSr0h0/2/RCf8i976IjCRAHSodx9dUz8I5En9ItY8NoeuvUv6edEJ/zaj8rOG1f4Xd+KIvQ4UKCkEpUk5BBwQR2HlG8bIa+Za/5Jyq1h1Er1bwUqZm1dWCUHGd444xHilnPi5J7MQbqzoWnPvD8UfVWxjOO1nxyWHk3PaXWnpu/Kw5I1eZXKmYHVKYm17hG4nhuqxjOeEaluDOgyYpQ25jRpz7w/FHqAtPr0KTrzSRCqMIJRRi5LOTy2Q1j5htvlJqjqwzIzrngkyo8A1MYTnyBwIOToMEx2bPseCzbiMYGSU+SOJrmpaatJeIEl9sEBKsYWk8UmJo6O21k12SbsO6ZhZrMqginzTxO9MtpGrayeLqRnj65I5kGOPUUuEty7HrVWLUVYfdE09cBqTB4SMaERFnSBvGZtHZ1PzEk843VJtaZGQ6onfDq+Kk45pSFKHfgc4wfR+r9xip3FYd5VB+cr1IfDwW+6XFqZWE5AUfXBKiD3BYEYqC7MwUJOveic2qpMtjd3kuJHJYziKHJyYfVvOuE93KIasOtVmZ6QN8UWcq02/TZOXQqVlVuEtsn6VkpHL1x9MeHSruGuW7ZNJmqBWJ2lvuVIocclXShSk9Ss7pPMZAPmh04+SM9s3JQciaethF3GsRT0o6/VaDsmn6lQ6hM02dROsIS/Lr3FhJWcgEcjEgWo67OU+llxSnHFyrS1qUclR3E5J8pMHEwlBqKl6vBEHTWuMNUq3LFlXCp5xw1OabSfYjebaBHesrI+0iMqdLpkpJiUTwaQAT2nn7sW20G4E3vtwq9ZbWHZGWe6iWVyLTHiJI7iveUO4xfb+eUdGkjtjkx9oT5UPQrzCKsaEmKSSOUUKXrHVk8/BJOwA/oun8f5uPwrcRZtnz8/6oH/AHpJe8zEn9H05u+f/k4/CtxGO2cf3/Kgcn9c5L3mY+S//Zs/Kj7LTLHsqv8AMfQ+FD5wlaAk8IxO48XJVlc23NKQetbBCTnhmLesVukUWXMxV6nJ09kDJXMvJbGPOY5+6SvSCXaM69aNlqYerjeBPTrid9uSyM7iRwU7gg9ic65OkQLamzDaHtPmE3DU3XfB5g74qtafUtboPNpByojswEIxwjeq0o7rHhHJdqo1naCtsmyccdo9q+aptH/mjzO2fZMP/wCI1se2Tfxxza30YKmUjfvaRz3U1f5yA9F+o/XtJe1qvzkYdXSffOb7SXodI/Pp2Tf6RbY9sW/jgG2jZN/pGtj2xb+OObPoX6l9e0n7Wr/OQfQwVL69pP2tV+cjHq6T74+0o+h0r8+jZN/pGtj2xb+OD58+yb/SNa/tk38cc1fQv1LP7NpP2tV+cg+hhqP17yftav8AOReto/vj7SidK/Pm2T5/bGtf2ya+OEds2ybP7Y1r+2TfxxzX9DDUfr2k/a1X5yGejDUfr3k/a1X5yJ1tH98faUfQ6T+fPsmx+2NbHtk38cL58+yb/SNbHti38cc2/Qv1L69pL2tV+cg+hfqXO9pL2tV+ch19J98faKOkTtm2Tf6RrX9sW/jij58OyUqB+eLa/tk18cc4jowVH69pP2tV+ciodGGoD/HaS9rVfnIqu0n3yfaEX5HSI2wbJca7RrWP/wCSa+OPRna9snUtKG9odqlajgAVNnJ92Oaz0ZKgP8d5P2tX+cjyf6M1VCCWr0kFK5BVOWAfPvxeto/7g+0Y+h2VIz0lUJYTMhNy80yrgtlwLSfOI9VR876rQdpuxWrNVeWdfpTQdATPU18rk3ifYuJ0Bzww4ka4wc4MdV9HPbXKbS5BdLqbbEhc8o3vzEs3kNzDYwC81nXGSMp1KSRxBBOx1rG6Dyjrq1EbETIdRwhawwDD5xrNwsawQwMiLOrVOnUmUVN1WelZGXSNXZh1LaR5yYhC65QRHru2zZI0soVtEt4kfUTYUPSIpG3DZF/pCoP4x/VGfTn6EyiRIpIxEefPw2Rf6QqD+Mf1RV8+/ZFj9sKg/jEOnP0LlEgweaI9+fdsk5bQaDj7og+fbsk/0g0L8Y/qh05+hNyJCgB1iPfn3bJPr/ofmf8A6oQ237I/9INB/GP6odOfoNyJDPDIjzwAeMaAdt+yPntBoP4x/VFJ23bI85+eFQfxj+qKq5+g3IkGEYj759uyP/SFQPxj+qD59uyPh88Kg/jH9UXpy9C5RIB15QcOUR/8+3ZHj9sKg/jH9UVN7atki1hCdodvgnhvTYSPSdIbJehi2mb9iDHOLKj1ilVmUTN0ipSlQl1DIdlnkuJI8oJi+zpprGHYxyLEEVCEfJAogIBD5wQAQocLMAEEOFxgAgggMAIwQ+cIQA4IXLSCCBUOEEAggQIBBBEAQQQRQEEEGIFCCDyw4hBQ4OfGDzwAQuUPzwZAHjKAHMnlFBGHSA2sSezWhNtyrbU7cE8k+Ayi1EJSkaF5zGu4nsGqjppqRyPKW3tL20Vx6pzDz9WAdw5Nzz/VyUqQPWITqE4B9ahJPbxJj1qE7O7atuDjyJhxtirTZbYcA1l5FsHdIB4HcBVg8FLMdI3rdFN2e29I0K3pGWaeDW7KsY+lstjQrUBxJPpOTyMepRSopYWWzyNbrHB4RE8p0ZJ9LY8KvKXDnMNU9RSPOV6xdDo0OY/Zkn2v/wCuLOoXvdk4+XV3DUEE8mnerSPMnAixVdV050uWsfja/jjs8PP1PHettb7mb+hoc+vNPteflxUOjO59eafa/wD64wQuy6frlq/42v44Yuy6frmrH44v44eHn6k8baZ0dGdf15p9r/8Arg+hmWR+zNPtf/1xhBdl0/XLV/xxfxwxdd08rlq/44v44LTT9SeOtMz9DK5j9mafa8/nIX0MrvH5s0e1x/ORiPmrun65Kv8Aji/jhfNZdH1yVf8AHF/HF8LP1HjrTM/QzO87zR7Xn85B9DM5jW80+15/ORhvmruk/wCMlX/G1/HB81l05/ZJV/xtfxw8LP1HjrTM/QzL+vMe15+XB9DM5j9mafa8/nIw3zW3SP8AGSr/AI4v44Yu26frlq/42v44nhp+o8dYZj6GVf16J9rj+cil3ozObn0u9EBfLep5x7i4xIu26frlq344v44rRd91IWFpuSq5HDemVKHoORDw0/UeOtNXufZztB2VzZuKnzTzcswQv1XpD5R1eDp1qNCB2hQUjHE8o6L6Nm3P5u3Da90pYlrkaQpbDrSSlqebTjJAOd1wZ1TnUeMNMhOM2V3+/X5pVBrzbDky4hXUuhGEvpA8ZC08M4yewjOnbz/tmtqZ2X7UmZq2VrlGxuVOjrSThpQUQWs80pUMEfULA5xyX07uGuT1dBrXJ4Z9CBxyYr3kJQVqUEpSMkk6ARhrOrUtctqUq4JPHg9RlG5lvHILSDj3Ystpk07JbO7immVYW3TJhST2Hq1R5OOcH0CeFk4grD09t224rfZfWyxU3urlnN3JlpBrJSoA8Du5Vg+ycjoW7qvSdmVtSNBtqmsJcDZErLY8RtGfGdXjVRJ86jnviEeh022NpU28UjMtQ3EI7t55ke8MeeNw2wTKpi/6iFnPVpaaRk8EhAOB51E+eNttcb9SqX8MUfLa694Zjnr8vSYcLjlemW8+xZSlCR5ABCTel3H/ABin/vx8UYIJ0OkUkER6C01S/pR5G+T8zYRet3fXDP8A34+KKxed2n/GGf8Avx8UauiYQVqbC0lSfXAHJHlHKMTedcco9HS/LrQl5x3dClDISkAlRx5B7sOhV91GyELJyUUb/wDNldvK4Kh9+Pih/NjdvO4ah+EHxRqchs72+T0mzOylqzS5d9tLrSzOyKN5ChkHCnQRoeBAMYWTm7ppF6PWtdkuZWeayl1he4pTa90LT4yCUkFJ5ExI1US7JHVZoL647myRTeV2D/GGf+/HxQvmzu364Z/8IPijAqUlCVLWpKUjipRwB5zFTSd8BSdUnUEcCIy8PV91HA5SSzkzvzZXbyuGf+/HxQfNldw/xgn/AL8fFFdBoUpNUqdrFWqKqfTZNSGluNsF1xbiuCUpHdxjIos+UNxTlEerBS83J+GyjjUvvJmGd0qyST4vIY8saJPTRbTiv2Kt78zFfNrdv1wz/wB+Pig+bW7vrhn/AL8fFFxb1rStQplMmZ+s+AP1ZSkyDQly4F403lqz4oJ0Hmi3kreYTJuTdeqopLXhypBvDCnip5Prs44IH1UY5033V+xff9RG9bu+uGoffj4ooN63cNRcU/8AfD4orVa/VN3CzNVJSKhRElxbKWMocbwN1QWTpnJ05RdyNmNvtSsm7WUtVudlDNy8l1BKCjBKUqczgKIB9EXOl+6v2Hv+psGz7aZOmps025nG3Jd1QQ3OhIQttR0G/jQpPboR5OEfdKzZvTqFPMXXSZVDElVXlS8/LoSAhEwUlXWADhvgKyPqhniTGNVuvsEYJQtHA8wREvdIHM/0b3Zp8lTwRTpjePHf65oE+cKI88cltUdLqITr4UuGj0NBbLdjJJHRhvaYvjZJT56oOdZU5Fa5CdUTkrW3jdWe9SChXlJiUOUcy9AR5Rtq7GM5QKk0seUspB94R00dBEuio2NI+vplurTZ8+JVw/RTO6Y/RXNj/wAxyJJ6Rbh9UaFr+4v/AJSIjKSOelK9/wDVc38K5EmdIgf3QoZ/1L/5Tcc9n83o/KzTLn2Vd+KI3pc29IVBieZShTjKt5IWDuk4I1xjtjZRfNXzky0j94v5UazJOyzbwMwguIwfFBxryjICdpGP1E56f64+udUJ8yPh7I7nyjMi/awOErI/er+VFhXbrqNYkBJzLEqhAcDmW0qzkZ7Se2LLw2j51kXT5/64s5pbDsyVSzam2zjCTxBidGEXlEhVFPsYC6K6aXKgNkB9wEhR4IA4qiZujvswbocq1e12Sy/Vp4KNPlHxkyyD+6qHJxQzx1Sk40JOI12UUFq8NuFMlnUh2UkFGcdSRkFDBGPS4pHlzHTdSmy7OuOBWUgkJ8mY0STnLDPWclRWtq5ZEe0ujXLf+2SUplMW/SpC32PCmahMyalsKmQpKioZwlaslAHHG4vvjH1qmXvYm1Ch33Vp9y6fCVmTqLshTlJcQxugHeQgHIx42calAHEiJnE2rGCYPCdc72IvTZjHVrCWOCEpm4apZm3u8a8bTuCrSc8lLDKpGTUoK8VlW8FEYI8UjQxkNqLtY2u7JnHaRblYps9TKmFCSnmg28+gtFKlIBxnG+DjnuqA10iX21PvnDKFrHdnEUuLdaWUOgpUORibPqPFxymo8kGbR7wuLazbEtZFLsWtU+ozUw05OPTjBbl2inOoURkJyckqAOBoCYmy+62iyNktXrLbmXZWTTJyaiCN95QDTfDUeMoHuwTyj2M4ocVKPYMxE/S9uINyVv2PLr3nf1wmkpP2zbQPblRcP82MZwa4NldytkklhLkh6w5FMrSlPJGOsUEJ+1SMe/mM3Pz6JGWU85rjRKfqjyEOWZRKyjTCSAlpATk93ExkNmFnK2l3kpmcS83bVNR1tQdSd3fT7FkHktzu1CQToSDDU6iGkpdkuyFFEtZftXOTXqtSajJWxRrmnZpbUxWnnFSMv7JcugD6d3AqUABzGvMRmDkHXU84yu3aois7ZlSrO6mUo8q1KtsoGENkAuKwOHs0J8iRGHCiRGv2dbO6hWz8+S+0qoVXdOHkSV0eyfmwn/5OPwrcRttmOdvVR/lKT/JZiR+j2o/NdUOH63H4VERrtnONvNR/lKT/ACWo8L/9mz8qPeoX+FV/mZ9EY0jbjeJsPZfWbkaCTNMNBqUSrUKfcUENg928oE9wMbsI576d0w43stpEulRDb9abCx27rTqh7oB80Z1R3TSOi6e2DZBPRq2fs3nc83W7iSqepVMUFOpmDv8Ah02vxsOE5KgNVqz64qT3xM+0naLNU+pOUa3uqQ4yd2YmlJ3sK5oQOGnMnPYIsuig23L7H1TbaQHHajNurPaUYSPcSIiuXccdl23XVqWtxIWtROSpRGST5SYzhUtVqZOfaPCR8hrr5KW02UXreBJJuKf17FJHvCKxel3Y/ZDP/fj4o1xPlipJj0vDVfdR5rnL1NiF6Xd9cM99+PiioXndv1wz/wB+PijXQSYqChmHh6vuom+XqbB82V2Z/ZDP/fj4ooVeN2/XDUPvx8UYVOTGBuC7KXSkuNpcTMvo9clKsIR9svh6MmI9PV91GdasseIm7fNndiclVxT4A4+OPiipN53WRpcM+QdQd8fFGrWjsr2kbR3G5qeaVQqGrxw/NIKErH+rZzvrPerCeYJ4R53Xs92h7MVvPqlvVigNje8LlwVtJHPfbzvtEduqca5440Lwzns4yd8tFYo53cm4C8bsz+yCf+//AKoZvO7B/jDP/fj4o0iiXRSqqENodEvMKGjbh0V9qrgffjLuaHB4iOjw1X3UefJWQeJZM8b0u364Z/78fFFBvW7T/jDP/fj4owGYR1i+Hp+6jHfL1M6q9Lux+yKfx9uPiilF7Xg2oLRcM6SOSilQ9BEYPnwhgDOcxHpqX/Si9SXqTRs8uiXveSm7euSSlXnnGVBxpTeWptngrKTwIzqPOOeOfLupk9sS2wNzVBW696nKRPyHWLOX5Ze8CytXPO6tsnXgFcY3zZ1NLl75oq21bpM0E+ZQIPuGDpmAeqFrTQACy1MtKPaApogebJ9JjzYVrT6vpx+GS7HraC+WMHYdNnZeo02WqEqvfYmWkvNq7UqAI9wx6kZiPujfNOzewqz3Xlla001tvePE7vign0RvU9NNSUk/OzK91hhtTriuxKRkn0CMHHDwfV7srJEXSP21MbNKe3SaMhicuecb6xll3JblWskdc4AckZBCU5BUQeQJHLdu2ttF2y1RdaqE3MTzJcIXVKm8QwgjQoaQOzXRCQMg5IOY87Wlp3bbtocm60460ipKXPziULOWZVG6EtJPLAUhGRjVRIwY6H2iXmxZUrK0C35OVbmksJ6trq8MyjOoThIwCTg4HLieWfU09G3t3PC1+uceER230ZZjc+m3oyVc9ynHHuuRV9DMv680+15/ORjpi9LsmHS45cNRBPJt7qwPIE4EeYuy6OPzR1f8bX8cdvhp+p5D11nkZX6Gdz69E+15+XFQ6Mzn15p9r/8A/pGI+ay6frkq/wCOL+OD5rLp+uSr/ji/jh4afqYvXWmYHRlc+vNPtefzkP6GZf15D2v/AOuMN81l0/XLV/xtfxwvmsujlclY/HHPjh4WfqTx1pmvoZnPrzHtf/1xT9DM5yvNPteflxhvmruj65ax+OOfHALruj65axj7sc+OL4afqXxtpmfoZXc/s0R7Xn85AejK79eaPa8/LjDfNVdH1y1j8cX8cHzV3T9clX/HF/HE8NP1L460zP0Mzv15p9rz8uD6GZf15p9r/wDrjDG6rp4fNLWPxxfxwvmpuk/4y1j8dc+OHh5epXrbTNHozkcbzGf5P/64tpvozzBbPg95thfLrKcd33Fxjfmnuk8LlrH4658cekpdt1yz4dRcdUUocnJhTifQrIPoh4eXqRa640mvWbtF2QVdFZk5p+nt9YEt1WmO5ZWo6BDiSOJ+pcSUnIwSY6s6Oe2BjaLTnKVV0sSdzyTe++w3kNzLWQOuaB5ZICk5ykkciCcNs5u6XvSnzdAuKTlXphTKutbKPpU0zoFZSeBGRkd4Ixrjnq5EzexPbKibprrrrVKdROS+8vK35NYO82o8yUhaMnmkExx3UqSafc9jQ61zwpHffDywRSy+1My7cwwoLadQFtqHNJGQfQYqjyz2gggwIIECCGNeEIRAEEBMGe+AFBAYBFAocKH5IhRQQ4UUFUHOAcIO4wIBggggUIID2wQIAggEGcQA8wtOyCCADzQQQQKEY65lqRblUWkkFMk8Qe/q1RkYxt0a21VfuF74NUERnC/RCSPnnyyiBlugvrT3HLCc+gmN320zK3Nok4FHIbZZbT3Dc3selR9MaR0RdNpbP/0+9+XLxtm2NX98WpfatfBpj6CnufLe0Obf/vVmrzU7LyUquZmlFLaOzUk8gO+LClO3fcLa5i3rccmZZKinfQ2VDPMbxIBPkjA7RH1pkJdCVFOq1ecJ09+J/qlQNGZk6PSCJOUlmEhCWwBpqP6M+eN+ZSlhHPNRqgpNZbIpVb+1A/4pP/g0/Lin5ntqI/xSfx/Fp+XEmIuKpjjPO+58UVquGp/w1z3PijLpy9TT4pfcRFFSktodKknJ+o2u6zKsjedcUzkJHad1RIHfHpR61K1SVLjJ3HUY6xsnO7355jviUZW5Z9iaSt55T7R0WhQByO6IzvjZ9VafX01qxZAzNOmxveDy+7/a5PFISSMtniAOByNNIxlvhybqpV35jJbX5Hv1nLjBvGMQ3R9pAGtsTH4D/qj0FK2jDT5l3/wH/VFVpHpvqjKb0PMYr1M2j/WvMfgP+qD1N2j/AFsTH4AfKi9VE8M/VGW3vJC3hzEYn1O2jY/YvMfgB8qPJyS2jD/FeY/F/wDqidVFWlb81+5misdgg3+Gka3Ta0+J5VPrEqqSmkq3SFJKcHkCk6j3o2JKe0Y88ZRluMJ1OvuZ+w31s3nRnEKKT4c0NO9QB9wmM70yG2lsWxMEDrErmGwfsSEEj3BGr2kvcu2jfd7HwiY2HpguE062/wCPe/JTHPf8SZu0fFiR0B0XXVObBLUKjndlFIHcEuKAHoEbDtbGdl9zD/dcx8GY1ror67ArW+51/CrjZ9q43tmVzD/dcx8GY+el8x/ifYx5rRxx0QTi/qqBzox+HajZtqqv74FTJHNv4NMa10RMDaBUz/uZXw7UbBtWV+j6p9u838GmN8F/30vwPjtZlyMC2QdMRr14V9UipNLpba3qi8pKAlpBWpKlaJSkDVSzoAB2xl0OKScxg7LuOX2d7YpG5anJpm5BC3FOKW3vqabc0U6j/WI178ZHOPSk8JmOh08bLfeNjnujxtIp1qS9xyC2pmuY6yapDDoEwyk9jhVuuLHFSfKAVY18LX2G7VNoamDW5MUCk7usxP7rbhQr1xbYTlW9j6vdA79RHZKplhMoibQ6HGnEpW0ts56wEZSU+Uaxg71uGlW1RlVm8a+3SJHewlG8StxWNEhKcqWr7FIJjhc5NYyfRbYxaajybkXZSWQiXbW22hCQhCN4DCQMAegRzb0ldjt6XJfSb7spqXnyZRlt+UTMJamOtbKhvo38IUCkpyCoHxdM5xHvM9IvZmzMBqWo1wTrZ/dgwhsehagr3I33ZztHsO9Jsydq156VqqU75kJtpTLixzKQoYcA57pVjniIoSr95De55Ukc62lsi2mX9Vi3XZOYt+lSqimYm59rq0pWnQpbZB3nFn6r1uM+NwBwtXlLg2WXOu2bmYJlV5cln0ZU261nAdaPZ9Ujik+Yns6fn5tboamlFK0Dhy8ojnHpeXjKzZp9gysq1NTzDyJ2ZeKMql1KBDbLZ5KUDlWOWBz03wsm5cnNZRTKDjgVu1ykPW7PUKruTTchOutzTc1JpC1oWkY4HQgiMgm7qcb4crJlX2pFFLVT5dAwV7u7hJVrjjmI7osqafSZeTUvfW0nCjyyTk47tY3C1zLyVrVmvuSEnOTUq6ywymbb6xtsLOqynmeUYXVQWZPzPn2sPC7IvLfuOhs0qhNVhqf8KoS1GX8GCSh9JO8EqzqMHHo74olq7RqtS1ydztzzW7UnKg2ZMJO91hypo73LvjPU6nUlN+syIosgqWqVNRNlDjW94OstrJDedACRmMdbTNNkrdtlx+kSU+5WZlTcyuZb31JSFhsJQfYnnnjxjRtr74BZuXRLzU5dc5NSzja61LdSylGCEY0G8c9mOHfGRkrqorL1Or0yxPms0+SEo2ykJ6h0pCglZPEaKOR8Wqn2KdaVGnp5mnSVSe9WlyKPDG+tCWUJ3t0D6o8M8Y90y1Mk7wua300uSdlWpJ2aYW60FusqCEYSlR4Abx9yK+m1wicpkbo8RvBOSB6Ylrbc5nozP6n9RyHwzMQ6HN5rJPERLe2g/wDw0vfcch8MzGHtD46vxOnR8TPToAn+4N3fygz8CI6gMcwdAEYoF2/ygz8CI6fjXqfms+yo+Wj56yCc9KR7/wCrJv4VyJL6RuPD6F/Ev/lIiNZE/wDxRv8AP9Fk38K7Ei9I5f8AdGhD/UP/AJSI57P5vR+VmGM+yrvxRF8oy/NTjEnKtdbMTDiWmkAgb61HAGTgDJI4xtR2bbQOVrzH41L/AJyNRk5p+TnmJ6WWG35d1LrSiM4Uk5B9Ijck7V77H+FmvxZv4o+slnyPkXGXkeA2dbQd7BtWZ7P1TL/nI1WdnDIMTK3k7jsvvJUk8lg4x6Y3VG1a+jxqzefuVv4oi2+phSJdSnFErdUp909uMk+kmI3JLJnVBymkybuihTm6daNeux0EPTTokpdZ5pb1UR5VqwftO6JCW6OUW1s2lOUCwKHbsuG2vA2AqbWo7o60+MsnHMqUoxiK7e2z+1XC1XbmbmJoHBlZJJeWPKGwrd8qiIxhtjHc2Ld1lm2KyZlbq8hKUkqUcADiT3RiL+vu3dnjMsirsPVKqzSC4zJNEDCQcbyidEpzpnUnBwDgxpdY6QcmlZlrOtJJcOQJifXrntDaMqPnUPJGqWZSaxfm1yQrV5y6JluYc+mNuICW1JQ2rcQlGuEAjOD38cmEpymvdQjTGp7rX2NntLbLc127SrdpQakqTS5icCXJaWBWpaQhRwpxXEaDgE8ImWt77tYebYQpahujCATyEc3XnVJe0+kR6uOyjjstT5hDpYY3UlSeqKQE5wBxEZes7fr5q61s2zQ5GlNEkb4SqZe8pUQlAP8ANPnjCL2y4N8q1bBOPCOgKdSZtL7czOoQxLoUCouLAz2dw17Y5S2g11F4bZKtWmXA7JMO9TLL4hTTQ3EkdoKt5Q7jHjU27wuZ4vXRXp2a3+KJmYLiR5G0ncT5gI9ZCjS9OSsNKWtS8bylYHDkMRm4yk8sxi66U0nlstplU9VqhL2/R2FTVQnHA02yDjfUdQnPIYGSeQBjqyy7cplk2tK2zTFB4Nr66fmQMKmpg43lHuGAAOQAHKOV7YqVxWhcMxWKJJyT844hTSHplrrNxKjk7vjJ3SdAT2DESlsY2gXldt3TchV0UwU+Tk1PPLl5YoUlwrCW05Kzx8c8PYmPi/8Aq2rW3V5jhVx5f1PsP+l5aOFiUuZst6psUuKo3BUat82cih2emXHyPA3MgLWVBOQvUAYHkAiM0Hwa4JinytYRWJVlSkeFtoUltwp0JTvalOdAeCuI0xEqbfr8ckZY2fRH1pqM2gGcdaOFMMq4Ng8lr541CewkGIspco3ISyWhulZ1UQNB3DuEd/8A01LW20KzUPjyWPI4v+pIaOm510LnzZLXR6WBeFQ4frafhW4jbbQR8/ao6cahJ+81EgdHpRN5T/Z6mq+FbiPdtBJ251E4/wAISn5LUYL+c2flRsqX+E1/mPooI516en7W1B/ltPwDsdFRzr09P2t6Dj/PafgHY3af5iMtT8pmJ6Lh/vJJ+7J78oxE8kf7Tl8HTq0+8IlTowLxsVSP9qnvyjEVSav7VZ/i0+8I36H51v4nxmv+aXGT5RFY4x5JXnlFtU6pI01oLnHw2T61A1WryAe/HpnHGLk8Iv8AvxGIrlwU+kZQ+6Vv40ZbGVefkPPFjRvmyv6fcptnUh5TaSEOvJWEJbzjVx0+KjQg7oyrHAGJXoOyPZ7YjbdSv+opuCpqGUSCUZYz29X65f2yyE9wMc9uohB7Vy/RHfVolH3rXhEV2lb+0Lai4kUKREjRVLKXJ5xRRLgDj43rnTx8VAxnQ44iXrctTZdspcS9PqN03KghaS82lQYVy3Eesa8qiV68eAFtee0mr1ZsyNLAo1NA3ENSx3XCnsKhjdHcnHlMR8tW4TpGEdNdfza8L0RslqlH3aVg3+79o1cuLeadf8Dkz+9pdRAI7Fq4r9wd0K2No1wUJKWQ/wCHyadOomVklI+xXxT5NR3RHxdWjqVu77TTysIcUg4UM6lOcBWOwGJMkbAnkU2UvCzLrotWlpd1DqFTRVK7riSCEL3shJyMEK3eMbp06eENrjwaa6r7Jbs8mOuCx9nO0gqnLffFt11Y3lMttpDTp11U161Wp9c2Qe2IruGRvzZ471Nw0/wmmhYQ3NJc6xlWeG65xQeW6sDXh2x01teodn1Kdp787LqtaoVJoOS9QSkLllv+yZf3MhKhoQ4Dr2nGDHUrdtVoU2/Q7jQzVpdpSmHkqdS8cDQ4XqlxPcrzkHSOelTx7nK9Gdt6dL22YkiP6FW5CrjEu4Uv4yWXBhXm5HzRlSnTMZKu7OrOuhpyo2RUUUucSMqklpIaB+19c35U5T2CI/narclqziZC56a8AThDiyCV96XBlK+3HHtxHVCal+J58tMp81/sbbkdkU73ERjqbVZKpNFyUfC8euSdFJ8oP/8AKLve14xmc0q5ReGZ2xlYvSjH/bG/fi66Yx0tfyzP/txZWOf0ZUbh+rG/fi76YWqrYzwBmf8A2o8u9f8Ae1/gd2h4kdCdGA52CWl9xf8AMqM3tpfcldkV2TDZ8dukTKk4/izGD6MH7QtpfcX/ADqjKbd1EbGLxPD+40z8GY1y+Z+p9f8A+v8AQ5Z6HrbQum4nt0b7dPYQg41CVOKJHn3U+iLnapMKe2h1lSzndeSgeQNpEWnRAP6Irk7fA5f4RcVbTT/fBreuf7ZH5CY96nvk+P1vzTBb3dDJ7AI8t7AgyMcI68nJgrz3CDI7ooyIM90Ml2noFY5Riq/Wm6SlsFgvLcBVje3QEjmTGQJwOEYSpq/Rva+cfrjK5/Gm4wsntjlHRpqVZaosx/zdy+dJNP4b/pg+bxj+Ap/DH5MdwbZdrFJ2aTdIlZy3qjV3qqXEsIkQ2VAoKRjCiCSd4YAzGkO9JBpJx86O+/xFA/pjzIa26ayonty9maeLw5HKvzey38CT+G/6YfzeS2n9pJ/DH5MdSHpJNf6I75/EkfHCHSTa/wBEV8/iSPjjLxV/3TH7P033jlz5vJcfvJP4b/pg+byWx+okY/jv+mOpR0kWzp86K+fxJHxx6J6RjZGTsivvH3E38qJ4m9/0jwGm+8jl1i9Gnc7lPCjjJw8TgdvrY2GkT7VSkRMttlshRQpJOcEd/OOojftK2kdHq5rmptNmJBhUlOsdVM7hWFIRqcpJGDntjkOyXwaO4Br9PP5KY36XUytbUljBx67QwpinEkzZTNLZ2g0gpON9xaFd4LasiMT0wmkG8KNMYG+7SVNrPaEurx+UYuNmSz88CjH/AF6vyFR4dL05uegjjimu/CmM7lzk5dJlWYOudl7y5jZvbbzh3lrpcuSf/DEbFGs7JjnZfbH8lS/wYjZo+fl3Prl2CHCgjEDik8eEOEYoH5YUHmhQAzBBCgUNIfKA8YUAEOFAcCAKoXOHy7YUCDxAIUHKACA8OEEEAOEfJBBAo/TBBBABBBBABGNuf9jFV+4X/g1Rkoxl0fsZqv3C/wDBqgiPscL9Eo42ksn/AHA9+VLxtG2NX98SpHua+DTGp9E87u0dn+QXvymI2ja+sHaHUj3NfBpj6KlHzGt+d+n/ACyLr/1k5fOui/eETPe88xKTa5mYJS01LBSiBrgFUQ3fSC5Ky4TjJ3veEZbaLtApFQcmZOW6wocaDaHnCEBWFZyEnXEbFNQy2YyplcoJIzLNyVqbYTNU6yLinJZfrHmJN5xtXI4UlBSfMYpNeuj/AEe3T7XP/m43HZV0n6RZWz2kWqu25iecp7HVl9E6hCV+MTkAjI4xtH0YdII/YZOe2CPkxwS1mozwj017P0qXJFCK5cvstn90e1z/AObi7k7ru+VBTL2Rdjac53RT38ejqok36MKkgfsLnPx9HyYpPTEpIGTZc2B/KCPkw8ZqF/ST7P0jI8N73x9Zd2e1z/5qKfm3vj6yrs9rnvzUSJ9GPRx/iZN6/wC8W/kw/oxqR9Zk37YI+TDxl/3R9m6T6kcm9754fMTdftc9+aik3vfJ/wASrr9rnvzUSR9GLSPrMm/bBHyYqHTEpB/xLnPbBHyYeM1H3R9naQjBV632o4Fl3X7Xvfmo9G78r0k616uUWt0hp1W6l2clFNpJ8i0Jz34iTk9MKjD11mzg/wDv2/iiNOkFt2pm1Kh0qmy1FdpipGcMyVuzKHN8FtSd0YGnrsxnVrLnJblwY2+ztLse3uPbdLyk9bNLri2UInQ94OtYGpQUqOD2gKTkdmTGEk5gvyMu4okqU0knvOIwd3X7J3FQZajIZSwpp8OhSpgHe0UMYwPqvci+ocyw9SmEtLyptAQsY1BA4R29SLlweXKmcKkpI2S1FZu2jan9XsfCJjael8P7m25j/LvfkpjUbUWPmso5yf1fL/CJjcOlwP7mW6rl4S8P+BMareTHTLFyJ76LA/vB2r9zL+EXG0bVTjZnc38lzHwZjT+i9UZBvYRazK52WS4mXWkoLqQoHrFaYzG1bWyv52Nz7icn1LmNP/DMfPyX8R/ifYRa6aOO+iS4BflTGdfUZXwzUZ7amsKv2p4Psm/g0xp/RVmmZbaLMtPvttqmqUtpgKVjrFhxpW6O07oJx3GNq2ooKL8qSjzLZ/8ALTHRBPxsm/Q+R1aamaFc9Xmqc6xKycsH5iY9YCCdSrdSkJGqlE6ARm7c2LbT7uuWmi67bmqXQeuHhkw+401uMZ3lhKN/rCVAbuQNM55RgZx7c2iWiskAJqkmcnummzHZs7POKnXw6lR+mqxvZ4ZMddueyPQ0cYQqUsclwurSMsuaqU6pMvTqYwXFYGEtpCcnTuSNI4zrdcqm1q8Zq5q664zJoO5LSqVaSzWcpaTyBxgqVzPmA6S2vBbmxO9lMk75knt/HHc3E73/AA5jmawAhNupCCAQ8vfx25H9GIlUUnkaq2UacruzNtUajMI3G6bKFP2TYUT5SdY1u6aCiXb9U6Kp2UmZc9YAyspKca7zahqlQ46HyRtRXFJ3Veu9bz8nON75PIpunCaeSc9iF/TG0TZ0mfqO6a1S3fBp1SRgPEJCkufzknUfVAxpPSJ2bXDc9Zpd3WZT1z9RaaEtPMNvNNrIbJU06OsUkKOpSQMkjd00MYboTpdTNXfjf8F8GlACfW72Xvd3ce5E2JmdEpwc45RzKGHwe/Jpc+pye/VLmoNdZot1UJdPmnN09W6jq1hKjgKGCQRkEadhiQrQfuBmbmEUGWVNFbY8IYLIdQpIOhUk9hPHvi06Uh/R7aq1gpc9TwDka4EyrHvx62nOlm6qfuOKQDMpSrBIBGeB7RG5rNeWeRrYKMltRkZabutdam68zLvvzksVNzDhZBS14pBSRwGBnSKbVq12S1IWmhSjkzJMrKwsywdDK8aqQTwOOzMeNInHVXzcSetUGy1P+LvHdJ3tDjhmLu10Tk/TrTmaZMhqWpqlCofTw2G1BW8VKBIzkZ119d5Y0ylx2ODGDH0Ss3PTKVMVOSaW/TnXesdefZDrZcyBv5Pss417Yokjdm5OXKzJTTyJtlxt+bW0FBSFY3iB5hqBgCLmTeZmbdvVcq4fBnXkrYTnA3S6TkDlnjGz05ThrlMuFDyUUFijhl1XXAIQoIUFNlGc5KiOXLujGTx5DdjgiopCUEDhuxLe2Yn6Gx4f7JI/DMxESQUS4C9CEajzRLW2VxB6OcwlCt4CVkgPM81HPr1mdX4nXpeZJl50Av1hu7+UGfgRHTxjlvoGz0lLUG7ETE0wwtU+ypIccCSR1Q115ZjqBp5t5tK2XEuIVqFJOQfPGrUr+Iz7Khrpo+fEgQelC+f/AJsnPhnY37pIL/unQgD+4P8A5SIjSVmmZLpKTc5OzDcvLNXdOlx1w4SgeEOgEnkMkRJXSRTip0LP8Hf/ACkRz2p/a1D8trLwvZd8fPKIrSrXnHqkZ5x4AjMezY14x9Zk+RZcMpjW5ucmnbqQ/JseEuSjqC2gtlaSUKz4w5jezkRuEiwXVYSMnGc9kZGUlG2E9Sw0hAHEJGNf6Yji5djCNyg22YesvbQLxeL1xXBOdWr9xXMFLY8jTeE+cjMU02waa0B15dmMcvWI9A192JOte0nJtj1QqLhlZIa7x0KvJ2Dv58oyk/IyLq2006UU0ygFJWfZn/vtjKNUfM4b/ac1xFmh02gysmkCUlm2ftEAH0xtdjMCSuunzcytLTTa1FS1HQeKoanzwXApFDt6eqziE/2sypaQrgVcEjzkiNCtCn7bb2pa6xatPmqjIIeUwX2npNhAcTjeSA6pJOMjXBHfC2yuruTTU369NxZt1829Sand8/VlS7U2XFjdcV4ySABwB07YxD9OQ2jcbbShI4JSAAIxF3UzbdZ9IFZueRmJCndalkvKfk30havWhQaUojPDPDOmdRG8W8PV22afVkoGZlkKWEjQLGQoDzgwqsrs+Eurqv0cU7Hwaa/KKTwziLZxje8UaHsMSRTKbTmJwuVaTU/LlBTgD1pPsu/TMeF02X1El6qUVap2QI3iRqpse+QPSOfbFcTXXqk+5FtRV4JKPPL0UhOnl4D3Yzez2vy1h7J5y4i2h+qVudW1T2VD9MS0NzeV9glW+T26AcYxd1ScxMUstIQVkLBOOJT/AE8ow8pT5qbMs9UitTEmwmXlm1jACE8AB2ZJJPMmPN1+i8XFVy+HPJ9F7M1y0ebV8XkWlLlJpbztUqT7szPTKi4t105USeKj3n3BoIyJOvGPZ9UWq1dkdkYRhFRj2OWyyVsnKRJvR5UBeFQx/m0/CtxH22U5241I/wC8JT8lqN66O53ryqAPH1NPwrcaRtsCWttlSWshIE5KqJPADda1j5dfzmz8p9VDj2RX+Zn0TjnXp55+dvQcf57T8A7HQDFSkJhwty87LvLAzutuhRx5BHPvTzydnFAwP8NpH/kPRuo+Yiah5qZgejOrd2Lp1/fM7+UYiqUJ8FZ/i0+8Ik7ozvMubJFy6XkF1iam+tbCsqRvZUnI5ZByIi6VKfBWdT+lp96OnRxats/E+M1fNrLxsZWATziNGJhIq8xV6lTHaxJSj+/ONF1baCgqISlbqAS2CdAeGmO6JGQsBQ1Ocxluh8v9F1577SHWzTmypCwClYDq8gg8o69Rb0a3PGTo0CS3SfkSBam0C3rntgUKwJyVtmbaR4kgqVShTSee4keKrj69O93xHtxU+u0uZWqstPFTiv1SpwupdPbvnUny4PdG1XhsRtK51GpWPNptasDxxJHSVWrtSE6tnvQcc92NQTeN+2A83QdpdCenJFwltD7u6tTg19a7kod0GcKwrGp1ji0VsIvNfn5PuW6hW+9W8npatDql0Vlqj0ZlD026CoBx0NpSkYypRPIZGgBPYDG6sbNaPP3FNWdI3rKv3RLtqUuRcpzzbR3QCpIdOhxkcM+TQxriabb9ysGqWXVgy6g7xYKlILSu3Hr2z36jsjaaNtcrVKkpqiXoxPMTrsuWpetyCGhPJA4AlYKHBx179Rzj0LbLJc1/sXSKj4bVybRszqc5d9qTFmz1Rk2KvQHimYYnJNM6iYlUq3VoU2D4y0EFIKTx3TrnXS13nYNFqszVrLk7ho8xuboaRuKkagkjg7LrV4o5jG6oajmQdUqu0W6KlJoYmKsoPJG6qdYbDE06j6hbreFFP2OcHnmNTW7vDAAAHACMoaRtty8/I3T1eEow8vMu6zVfD6g7My8jLUyXWreRJShUGGdNdxJOnmx5ItFTSiAD5gIqkadP1N4syEut5Y9cRolPlUdBGbmaRQLWYROXXPpddUPElUgkKPcgeMrynAjrUNq47HJKSk/VltbtMq1UfS/TQ41uH9UhfVhHkUNSe4ZjcLpuOg0ij+pd0vs1qZKfHlgwkqc7CU+tR5SQeyI9Xdd5Xi6qnWbTXJCRT9LU8hQQUj7JzgjyJyrszGw0Cz7btsl+vOCvVTG8WCPpKD3g53j3q9EY7VY+ESVezDm+fRdyMZdIRcMrNyMq7T5d99JYbK1LAbKt0gLIBWOIz8USIpG4cGPDbbNIVf1CAwkJlWcADAA65Wke7zu8TjtjVOKjLBjqJuajLBl7HUBeVH1/fjfvxc9L9wFdsj7p/wDajHWYT82dGI/hrX5UX/S1bWpdsqI0/tnX8FHlXf8AlwMtJxM6K6LuTsEtM/7Gfy1RldvOmxa8j2UaZ+DMYXoxT0g3sLtSXVOyyXRKbpbLqd4HfVpjOcxl9vyiNid6bo1FFmj/AOWY0P5v6n13ev8AQ5a6ImlwXH9xy/wi4o2mq/vg1vP8JHwaI8eiZNNNXXXJVx1CH5iSbLLZOC5uLUVY7cBQ9MLai62jaHXN9Yz4SPg0R9BSfJ6uLdpg94Y1h747TiLJU2xn9OTiPJVTkW1brk20k95Mb8mjpMyW/BvRjTV6YOM8z7vxQvVqlD9/Ne78UNyL0p+hlQod8YSq4N62x/KMr/6lEehrlL/hzPu/FGNmqnIPXXQJoTbXUS89LuPOE+K2lL6FKJ7gAT5o1XSTi8HVo65RuTZOnT0c3Z60lBZSUicIIOMYLWueUYLZPtfmnphq1bweeYqSSluXmnwUl3IBSh3PBZBBCjgKyOZGbbpkXhad5poKrXuCRq/gyJwP+DLKur3w3u5057piRtqGx2l7SbDos9IKl5G6mKUwJd9QwibbDY+lO9o7FcU55jIjyPFLTKG7zPT1FcLW1JmwpqCicFSgYrE8fqj6YgKy9olQthUxbN/ys8zPU89XvrRvvJwPWODPjaahYJBHboTmnttljIUUmoTAI4gsaj3Y9dTrlHOTw5aO2MmkskyeqSgfXH0mKjVFhpz6Yr1iufcYhM7brHJ/XF/8Afjj0RtpshxCkiozBUUkABg8x5YZqa4kFpb0/hZsvR4UT0Mq6Mn9LqX5AiCbEP8Achev7sfyRE+9H9vquh7cDZABSKmD5kCICsnSkrH+uP5Ijj0vzJHte0nmskbZkcX/AEf+PV+QqPPpbnNz0LT/AAa58KYp2aK/R9R/48/kKhdLFQVc1D/k5z4Ux1XHkab5p11sm/avtjn/AHKl/gxGzRrGyU52XWx/JUv8GI2ePnn3Prl2CCCCIUIWYcLEABggMECBAPcgg5RAELvggilCAwQQDKsaQocLl3wIGYIUECjgHZCggBw4BxgzAg4OHdC80GkAOA5xxhEwQA+ZjF3R+xmrD/Yn/g1Rkx3RjLo0tqq/cT3waoqBwh0VTjaGzp/gJ38piNj2vK/vhVHyNfBpjWui0cX60f8Acjn5TMZ7a8rO0Go+Rr4NMfQ1dj5nVvN//wB6kd3zMliSadwFdWlasduBHZVm25Q9nVtyVGotMlTNKZSucnXGwXZlzHjKUoanXOBwAAwI4r2gH+5X/hOfkx23cj27OM6/uI98x4ntiUm1FPgtlrqpWPMv/V+bB/SJX7w/HFQuWaH73lPvD8ca6Hd44GpPKNSubaVZtvTKpSdq6XppPrmJRtT6k9yinxUnuJzHjxonL4cnPC22TxFkpC5Zn/ISn3h+OEq45k/veU+8PxxBCduloKe3DL1VKfq+pSfcCsxt9p33bNzqLVHqrTz41VLuJU08B27igCR3jIjKWltgstMzlPURWXkkU1+aP7hK/eH44rFZnsfqWX/BH44ijbhVJ+l7MqhN02bdlJhTjDPXNLKVpSt1KVYI1BIyMjXWOe7dVedwVZqkUKer1Qn3UlSGGai4klI4qJUsJSBkakgagcSI6NPoHdDe5YNlSssju3HborU8DrKsfgjAK5O/wWX/AAZjiiSRe05QZyvy07X3qXIuhmamU1JzDKyAQFJ397Gvrsbo5mLBVYrg41ysZ/lB75UdC9kyfaZs2zX9Z3QK5O85aX/BmPRNbmhxlZc/+Gfjjg81utj/AA7WPbB75UULrFbUP19rHti98qH2RP75koWffO7pqoylWQaXVqVT5yTmPpbrLzAWlQOmqVZBjja/KJL2htjrVvUxSxTkOZl0KVkoQpCXAnPPdJIB7MRL/Rgqk/P2ypFRnpmcMtVOqaXMOqcWlBShW7vKJJGScZOmYjnbqpJ6QVZIP+SH/kJi+zoTq1Dg2YQsk1OEnnBjGJh6WfamZdQS+w4l1sngFJIIz5xE0bQqHK7WrClJmkzqJaaZdLzBWMpQ5jdW05jUDXiOwHURCIUY2KxLqnbWqZmGSp2Ud0mZbewFjtHYocj5j3fSuCaOGWU1KPdGBqOw3aHKST1QVR6fPJZBUpMnOJcdIHEpSQCSBrga6aAmJt6Ke27w9EtYV6T3hLjidyk1J9W8XhjRh1R4qxndUfXDQ66q3WgVyXm5Zmp050PSzycgg4yOYPYR2cQYiDpDbKG3mpi+bQlipDmXanIsjdweKphsDgrOqkjX2Q1znh1FCawz0dF7QbliXDLXpL7HXbBqK7vtFl1q3HHQtxtglKqU6ToUkahongR6w6cMY09q6Zi6Jpc5UC2mobiQ9ujAXupCd8DvxqOUTx0Z9sUte9NFgXypmZqxZU3LPvpCkVNnd1SvOhdA4j2Q1HMCHOkHsnntl1dRV6L17tsTTuJV4q3lSTh/cHDzH1KjxHinUDe5qrNsts+6OzV6WN0d0DW7hooqnVLEwWnGwQMpyCDrFNBu+69n9ekJ2ZrtSnaWl0KmJQzjjjbrQ9eAhZICgDkYxqBrFdEq7VRlsgBL6P0xHZ3juixtyTp90bUZSl193qKeHFJDSzgPlOqWc8t88TzGnEiOt8nBpXZGWyXZHXlKmpSddep0wpExIVJjAz61wKToP5yT7gjla6rdqmye7HaPUUvzVImDmSmyP09A4Hs6wDRSeeMjTEdDZWVErASc43QMBOOQHLEZGoP02t0pVJuylMVOTVgkPtBeo4KIPsh9UNYw24eUbsqUXGXY5warlGeb6xFSlwOxat0jyg6xha9cBniikUJl6cmZpXVJ6pBKlk+wQniSe3sib5rYnspmZgPS8/VpNvP6Q3P+L/5iFKHpjY7WoFhWQovWzR21TxSUeFuFTj2DxHWr1AOOCYyzk0w09UJbu4tklqnZvs29T51SDWqk4X53dOQhZSE9WD2ISMZ5qJPOI26Ql81eVq1PtW3KpNyDqmQ/OuSrpaWtThw03vjBGACo4I9cmJTn5x+ae62YJ3yMAYwAOwDsiIekdRKSuUptxCbTL1pREr1A9dNspyQ5pwLZON44BBA1IERRwdPU3NmhMW5OuTrc5VKs9NuoUFEqWpxSsHIBWsk4zG10+VYmGJqZnJ4yzTG5qlouLUVHGgBHZxjBPT8y3a6ak42A+psYB4KUTgHz8YuLUtraxctETVLdtmeqdMeWpAfaDCUOKQopIG+sE4UCOHEGJN4XPBx9K3UNmwsUSX9XxTJmpdW26lBZf6gq6wrxugjOnHieyLqk29Kzr9TlTUuqmZJLqw34OSHUN6b29nA1PCNRaqlzUi+Wqbdkq9Lz8qtCXWHkIDiCkBSBlOh07zxjZqZcVPplZqc7POllqdl32mtMkrcUCke5xhh4yjitpshLDPVijyztqzNaRUMvSqkJeliyQE7ysDC84OmvDujIy9qoeQxKCrIRWJmU8MZkywSkowSAXM4CiAfRGEkKrLtWnVaY6V9fNqZU3hOU4SoE5PKM1KXXR2ZqUrriZ01WTkPBESyUDqVqAKQvf4gYUdP+zJbzRtlk08uBxsK4hQ088S/aHqZfeyuYtCdfLb7cr4K9ujKkAHLbqQeOoB8oIiGWQUtpQrPigCMnQqnOUepNVGnvdTMNZwcaEHilQ5pPMRr1WndseO6N8ZOC4LWZ6Pd/uPrQyihT6EnCVic3Codu6tOnkyfLGx9HratUdktwzFq3imal6B1pRNMPhS3KY9p46QM/SyPXJTkahSeeZitG7JStyCZ+TV1T7Z3XmSclpWOHeDyPPy5jW9uOztjaHSjWqI02zc8o3ugaATaBnDSz2/UqPDhwMeZHVy39PUI9PS697km8M9+lTscRXmHtotkSyZyccbSuoyUvgicax+ntgeucCcZHskjTJAB5wauyo1umUunVOa8JRINrblH1ElZQopIQpXPG7oeONDEs9FnbI/Z88ix72dcZoanS1KPzAUldNdzjqlg6hontx1Z+xPi7H0pth6ZEzW0CypLellku1ansIGEE6qmWwOXNaR9sPZZ7apbJxjZ5dmerbDqwk4Pv3RB7SMHBJi5bTpmMHSaqh7dYdUCvHiKz67+uNxsmTFRrbTTid5tsdYvyDh7pEexBpvCPn7U4JtmSaaVSKUkKT/bczxz7FP8AV75jdNmdvMzrLlYqw3KbL/VD9MUOXeB7p0jByUmu57pRKypB61wMtKxoEjirycTEj3e2llLVt0ZaWZeSb3d4jI63BwVDmBnJ7yY245wjxtRa2lFeZHm2TaQmQJp1MKfDiBuNAbwlkngogaKcPJPLPkB1xVj7ZrCpUrehpE4uVmWy7NtB3wlbIzp4S1nOSMHeTkp1yU87jonSVIG3J6TvZl1debZcNNEyoKb8LSrLhVnVTm7qg8MBZ47sdqsPrSshRO9nxsx5V+rmp4j5H1Gl9nUVU7Zc5OHzUtom2iUVR7StRt2nhxHhDkuvDIUDnx33CEgA4O6nKuGh59cbF7JfsDZLSbZmltLnJZlbk4ppW8hT7ilLc3SQCRvKIBI4ARs3hjbKUydKlmQoknDaQlCTxJwIsqrNykn+vdxS8oCNUKdSj344L7p3Pk66Y0aatwqXH7I1LaTbLt8bNa/ajK2Uzk5LBcmXlbqA+2oLbycHA3kpz3Ry9LVfaHsfp6KXdlq+ByCnFlkTuC2Fq1IQ+0pSeOTu5zxjsWUbotUTmjV+VmVfUpdSv8k5i0qLk/JoVLTzTUywSPEfSHWyRqNDGdGrdbwvM02aeF9Sjasr1XJySmzNsl90qYu5FOmWpZhAck2FP+CrmMcfB2c5yBk7ysZ0wVcsvsa2jvKnPBZsgTYyl+WUClMwE6EgH1jg1yO7ygdDzdSmnptL631qeB8TBxu+TsjmXpXIpStq0hLWvLKRc7jKVVRUoQhC5hRHU6Dg7jVStNCnPd6NV892Jdmct+iouq2xWMEh7TrZkWJJu46GAumTJG+lIwGVnThyBOmOR8oiOlg1WTWwP1Qxqj7If96eiJZsJ1aXnLcrSkzEnUGurXyT127gkdgVr58RHtbpTlq3Q7LzBKhLubq1Yxvtn2XowY7sNPaz57T2Zyn5GgvoOdRgxbLTgRtN7SaJKqqKANx4dYnHDv8Ad188as8SRpwjFrDwerXLcsmybL7klbYvNioTrnVyTrSpaZXrhCFFJC/MpKT5MxuO2zZXVbsuFFxWy/JLfmGkNzUtMu9WhW6MBxCwCNRgEHsBBiIVDXURKeyDaE3TizbtcfxJk7spMuK/SSTo2o/UHkeXDhw+W9t6TUVWLW6X4ksNeqPq/Ymr09kPB6n4W8p+jI9n7IvrZRNyFzqlkUh5LwSxUKfMJcQhfJC8Y0V2KG6rhxjrKwrvtHpA7M52gXBKNN1FpCU1CSB8dhfsJhknXGdUqGoOQeceb/gFTpkxRKxKtzdOmkFt1p0ZTg8v6+RjmK67cu3YntAkq1QJ11TAUoU2fdGUvpI8eXfCSMnAyRoFABQ1BxweyvbMfaP8Ozixf6no+0fZc9BLdHmDPKtyl4bDNpS5OYUXQtsht3BTL1OWOmcAkBQPEcUK7jrVS5pmak2npdZU3uhOTxBAxg98dRSosjpGbKFIfQZeaaVhxAx4TS5oJ4pJGowePrVpOO3HIlzUev7NbwmaBXWAl5sBR3D9KmWicJdbPYceY5B7Y+kosTbUu58trdEpLfA2Zk+ONecWewS+aTYl1Vp6tNTHgdSlTL9cwgrLKkrKgSgakHONMkdh5VSE01MtofYWFtq1BjL9Ge3LeuasXdJXHS2Z+WakkOI3xhbR6xeVIUNUqxzBEXVuCqe/scGkjjcmS/TZyTn5FuckZlmalnBlDrSwpJ8//ZjKrqzU1T3KTXJKXq1NdG64xNIDgI8/Hz+mImrGy26LWKq5ssrkxWJMnLki6pIfweSkndQ5jvCVYGmTFnbu1aSffVTrnlV0SoNKCHCtCg2FfZAjeb/nad8eV0IzWa3n/c0OiyHv1PKMtdOxiVfmV1rZjWnpCeT44pz7xRunmG3OKR3K3k8sgcNRTfNQps0q3NpdAcadSkFS1sALxyUUDRQ4+OgxKrc4FBDzDuQfGQttXugj+iLipPUu46eKXdtKl6rKcUKcT9NaPDKVcQe8EGN9V1tfEuV/qRaqM/dtX6kUTltSs/I+qdp1Jufllahor1HcFHGD3Kwe+HJ0OQpUoKjddQalGU/uQXxPZkaqPcn0x6X1s4XYlNcvCzbkecpzbqEOtuqw83vqCQDgbricqSMKAONdYwVHs5dxSzVz3fX3Uyz3jNISvecWM8BySDg+KkZ8ke1prerHMOTa4RXLl7v+plJm+qhVHPUPZ9RVJwNHQ0N/yhJ8VH2yj6Iuabs9kKe6KpfFTcqU8vxjKpcKwT9ko+Mv3B5YumKuxSpT1PtyRapsrnJWlPjrPae/vOTFk5PYCnZh4dq1uK90kx2xrXeTMdzxitY/3N0r9Mr0lZktWWZCWo9GfWGZNhpYS44CkkKwn1qcDuMWF6VqzpK2Jam0WRQwhG67N1SaGHXXNwgoTzxknTTgMDnGh16/Z+qKlabTnZuqrZQGpZKypTbYHJCBx8unlMVyljTk1u1W+qk7KN8UyqFBTyh2aZCR3AE+SOdpya82v2M1CMFmXH+5rV93BLXNelPmqe26lhhLLCS4MKXhwqKsch42NeyNrTvDiYxu1CmUykXlRJOmSLUpLiVaVuNj1xLy/GJ4lWg1PZGSJTriNE4ve89zG+UXCO1cF5S5xchPS86zul6XdS62FcCUkEA92kSvtRtqT2pWVIzdFnmmJplZelVug7hyMLaXjVOoGo4EcDEMrI459EbFYt4TFszxGFvSDx+nsg8Ps0/ZD3Rp2RxavTyliyHxI54TcHlGq1fYjtApNMfq71KkJxmXT1izIzYceSBxUkYCjjjpr2CJ66Le2dm4ZJqwb0m0P1ItlFPm3zvCfa3f0tZOhcAzx9envBjaaNXG1MtTkk8l+WeSFJKDoodo74gLpE7MHKY8q+bRaWimqcDs4xKjcMksHPXt41SjIGcaoOvDhwV6rrPp3LD8mezoddmWCnpHbMZ7ZbcTN1Wf4Sxb7r4Uw8wrxqW+To2f9Wr2JOnFB4gHTXK+u8KpN1edbQ1OvqSp5tskJyEpTvAdhx5o6N6Pe1Gn7T7efsa+W5WYrng60ONuo+l1SXwAVYOm+MgKT/OGAcCCtuOzCp7JrlTNSKnn7dm3MU+cWd5TazkmXc5lQAyCfXDvBj09Pc4y2TOnVUKyO+JbS9LkXD9NQs9uFmL1m1LemFbzrD5UeJDxEYWiVhufa30YS4n16M+tPd2iNjknzjjHoNqS4Pn7VZB8vBdStgWi7jflps+SaUIzElstsJzHXSdRIPZOqEecg+pIGAkxmZaoOJxgI9B+OOOymcuzOd6uyH9R6SmyHZU4n6fJ1rXsn1xkGdiux1QBMpXvbByPJmrvp1CW/Qfji6brsyOTPoPxxwWaTUeUjOPtWyPmerexPY4UlHgVdwoYP90HfjiSn5mUalpKWpqnUtSjIabKvXAJAA15nA4xG6bgmQODPoPxx7IuKb7GfQfjjiu0Gos+J5Mpe1HNYZebYNn1K2o0oLBZp10SqMS08EDD6Bn6U7pkoySe1J1GmQYs2TbQapa9RNgbSZTwGYlSG5eZmkpKmCfWtuKGQpB9i5kjkTziWKVVqhNzCUMhlJB1Xunxfd4xDnSWvS3rjnJSlSMhLTtRpyimYqqNDjBzLp+rGTkk6A6DXONlGntf8GfK/wBju0us68HF/udApel06dQyD/FiKlzculteWGfWH9zHZEL2Le1r0C1JSmVO9kVCZZGqzLvENjk2k7mVJTwBPvYEZdzanY+4tPzRs5KSB9Ie7D9hHN4GcZ+ZzdSzdhcj6PDpPQ4rKc69XUvyBEE2acUtev7qfyRE39H5KmeiNWmljdUlFTBHYdwRBdoqApiv40+8I+h0ixNns+0HlcEg7NFYv2j65+nq/IVD6VSt65aIf93OfCmLbZsv9HdIP+uP5Co9OlGreuSinP8Ag9z4Qx12rg8uj5yOwdkX7Vlrn/dUv8GmNojVtkOuyu1/5Kl/g0xtMfOy7n1i7BBBD80YgBAYIR8kAEHGF5oOcUYCDlBBACMEOCBRCGeHCCErhAMqzmKYq5QoAUEOFAgQQ4UQowYOUKCBCrMKCDzxQPl3QjAeMLzQKMRjbn/Y1VPuJ74NUZIRjrn/AGNVX7ie+DVBEZwV0X1Yvps5/wACuflMxm9ri/0f1A9zXwaYwPRmO7ezZ/3Mv8pmMrtaXm/ah5G/g0x9JV8CPmtSs6l/h/yR9fR3qUf4pz8mO07nJVOsbuSepTp26mOKL0UDTD/Fue9HUe3a4HKHaE3OS6yiZclkS7ChoQtxRTkeQZPmjy9dV1Jow1Ed0IR9W/8Agjq77pui/rwTs82dIW7vkpmJpp0t9YEnDii57BlORlQ1VwGcgK3FVk7CNj0oy3tIqLdx111sLMoplTqQk80SyMhKMpOFuEknOvKPDZNNSWx7o2zu0DwNpderpSJJK0jAQo7sujI13AkKeUO8xmNg2xiWqMqu+r/Iq1anyJlxdQAdSyCAUkpVoXMYOSMIGEpGmuChtTXZI9aqEKIpRXJhmtsHRrnv7TmtmMnLyWd1L5ocsUq8m4d/Pux6VnYvs/2iUV26Ni1wJlJxk58C65aWQ4BndIVh2WXwweHPHOJzrEvba6cqTl2EzQOElt5kKaUnmClQxjzRAe0agTGymsS+0vZ40JNtlaWqlTEnEuttRwBgcEKOE413VFKhjWNiqzHMc/qYLWQc9ksEf3NelYndn9Xsq75d+Xr0nNMBKnk7ri9xxJUhwDTfA13uChr2Z8tktzUOl0yuWzW5l2jM1poJFclEq8IlinGG1boKi0eYHae3IkDpa0+lVyg29tToifEqDbUtNKTwcbWgrZWr7IYUjPPIzwEQ5s+VYbgq4veZn2CJUepplEuE9d42chIP2ON7xeOYzjCvpdjVOra2o9jZ9j1z0SzEVevz1QdmJjqFSUvQmUqDVQ3hnfeyN0NJ5Z8YZOOODH7j/WrUrdbRvKKt1tOEpyc4SMnAHADJ0jYtmatnaqfNKv8AcqaZvrEiXRJpdKNzdG9koHHezxjcWz0e0+uVcJH2s18UXqqube1vJrknF4wyKVDnFCkqxpGXutdvG4p35mTMGj748E6/e393dGc72vrt7jGLTumOqPvLJkmT30WFEUKaB/zuPg241bafT26r0lqjIuv+DpeUgFzAO7iXB5+SNr6MYSiiTHLNXT8GiNA25gHbrWtcjLfwKY86qGNU2cdcs22I3WV2b092YbaVcS0hagM9WjT3YznznqQBkXa5+Bb+VEHgIxgpSfNFbEsqZmES8rLdc84d1DaEZKj2CPZyaXVL1OhrPtQWtMOplrkVOyzw8eWW2kDeHshhWh7e0RuNKqDktMhCQXErOCgc+8f98Ii/Z7azNty/XPIbdqjww44kA9WD7BB988z3RtN53ZTNn9tqqk+EzFRfy3KSoVq4vGcZ5IHFSvMNcRZpKPvHJhzsxHuQt0j7QpVl3RJVO2Kg3ICdJeRISyy27JLT+6tFON1snGMYKVcMjh0jsKuSY2wbGlm9qK3MIcW5ITCloHU1BKMAupHLXQ9iknEc9bGtm1f23XrNXBcs1MCiNu/3RnU+KXljGJZn6kAHUj1o0HjHImfpG7VJDZtQ2rBsRMvK1kS6GwGEYbpctghJSAMdYQPFT7EHePIK8W/35qEe59Zp4OurM2czbSLdY2ebSqlb9Jq4qjEgtPVvFQKwFDPVO4030jAOO0HQ6B16jJqSBMMpDc0AMgnG8OwntHIxjrcpgK/D5srUSStAWSpS1E5K1E6kk5OvE6xsRcxqDHfCLSwzytRcupmB6L2j3tN0RugIWUTaE9W5OISRNLSOAKicJPIrGp7YsJW871stLZ9UlTsnqrwaYWX0kDVSUlXjJOOw454i88JV2xjrgknanJJQ0U9Yhe8kKOhGMERk0scGMb3u57HRswpsubzJy0tIWg59iRke4YiTa5edyUy627at+ZRKjwVpbrraAXi4veJAUrRICd3gM8dY1iUr20uVlWpaWuCYQ0ygIbSSyvdSBgDKkk+mMfLy9Ym7icrNdmvCJpQyp1SklS1YCRokAAAdmIjTM1OEctPJd0K6bssmbU6uY9UJaZJU4zNvKebcX9VvE7yV944888tz2a7Lbw2xPzd2V2pqplOdSpEtNuM7xfUNEpabyN1lJzrz1xkkmNGupkP0Za1kAsnfSSePIjziOm+iZeVQuLZgZGpMneocwKezM8n2ggKTn7JIUEntwDxJjnvlKK906dJi1ZmQtL7AdrUzXV0J+VlZenMKz6pOzwVKKTyU2gEuFWM+KUjGDkjQnrnZlb7Fl2BRrWbeRMGnSwaceSjcDzmcrXu643lEnzxh9o20C3rCoYq1wza20uq6uXYaTvPTC8Z3UJHdxJwBzMc+1HpRXRNzS1USzqezKJUdzwl119wj7Io3UpPcM47THM1Zd3OxdOnlcG29I7YncN33k7eVq1CSXMuSzTbtPmFFlRW2CAtt3hkjdGFAaj10R/ZXR3vC45OZn7un1264UKEqw6EzD6l8lOYUUobzyB3iOznIGzTpH0muVJulXjTk2/MOr3Gpxt4uSpVyC94BTRPacp7SInXRDgSsgd/KLusrW0xahN7sHAjrFdtC5Zi1LplVSs1LqA1VvJAPrVpV7JtXI+bQggbxZdDl7gqzkjM1ASISyXEqwCVEEDGpHbnzRiNtNfm7w2z1FdTZMkzTnVU+XlnNChllauPIqWolWexQ7It1YUdQD5Y7IqTh35PH10Fu90lAbL6bj9kyvwSPlRQ5sypoGBc6s/xSPlRGIaQeKUeiGJZk6lCNOeBGvoW/fPOdbXmS1bdlJoVVRUJO6FqI8VxtTaN11P1J8b0dhiQZKZMq91rfEcQeY7DEVWBZiJXq6zVJdPXeulmFJHidi1D6rsHLnrw36aq9Ot2jv3DX5kS0lLjIKhkqPIAcSonQDiTHj6uO6WM5ZpTlKxRjyzROlPaVDXRhfDL7NOqa1IYfl3Bjw/OgG6B+mpAOvApB3uAI2roW7RLluCQqFm1iXmZ+RpLKVy1ScO8G0k4Eu4Tqo41TxO6CDyJhiVVd3SA2mIp8gyqVYQnTfytimS2T9MXqApajyGqjgDxU5HTN4ViyOjpswZpFCk23qpM7xk5UkddOv4AU+8oa7o0yruCU8hHSouNca28v/Y+w0UJwjmZzr0pbAtuw7/lV23OSzDFUaVMKpLeipJQON5AGiWlchpgg4yPW12EXGrGnq0QA8sllCu0jQH0q9yI3nXaxdVxzVdrs47Ozcy5vzL6zjePJKR7FI4ADQCJNk5jqNncmzgJDs1jA00ClH/lEe1o4OKxI8f2pZGXwm7bCZUSbtTr0wn6XIyxSjsydT7iQP50XstUmGyqdqc5Ly++Stxx51KBknJOSYvLIbS1shqb6BhUzN7hI7PpafjiF7YsyX2ibdp+gVSpTcnKpRMvKelwlTiUshACE74IGc9h8kbZW9JOWDxdLpPG3STeMF7cEu1fu3OjSVkTimZt95hv1Rlsp3XGyVOTCT9igYB4KKQOcdn1lxap9EjLqIcdGVL5pQNM+UxHezLZtYezyoiq0OQn5irBlTHh0/NFxwJVjewkYQknA1SkRm7huH1Op1frCV/TZZkoaP1JCQB7pEeVbuus3JH0j6dFCrTNZvC952Vnl23bzhS4g9XMzTfr1Lz6xB5Y4E9ugi9ltlVSmXUOVCpS6N9ILrhyte9zGvHykxabBaVJvLma7M7yzKDq21KOcqIypRzxIHPvMZOt1uZqMwp511aWjq22DhKRy88ar5OqW2J8/KdaqVuoTee0c+Ri6zsmqks719HnJaaCQopUSW3AQNAMczwyCIsrA2gTUvWTa93BTrbivBmZmYVvONOg4Da1eyBOm9nIOOOdMtTa9NUqaS/LurU2DlxnPirHMY7ewxg+kfQKaz4FcMklLSZ/LbyEIxvKI3g5ntI0PmjGMVqMQtWcnTpLoxi79LmOO6zxg3bwYSFbl1vJ3mEuBQ3+zPPyRy9MSDVh9ImqIu6bXMgzDzyJ+Z1JDw3mnlYzwGUcMDBwABp0nJVn1ZsGkVhw7zzrDZdV2qxuq/wCIRqW0O1rMv19qcuWlzYqDMuJdE9JTRacCASQCPWqwVKI3gcZMd1SlGSeOx6HUhOuUJPua/M1OnzKRN0mpSsyAQpDku8leCNQdDyj023tpqMnRrkZQAJ2X6t3H1QG8PfUPMIhq67Pl9n+2akUmm1CanpZ5uWmkOvpSl0JdWtBQrdwDjc44HHhE3XOUvbFpV1YyZSoboJ5AqWn/AJhHd1Oqt2Dw79ItHbFReUyM7ibVN2rT59ZJU0rqln0p99I9MXVm2LT7ioKai9X/AANwurQpkIQrd3TzyocRrHlvpmLEn0cOqmAR6UH440KbYQSSpIJ7xGjXU22wSqntfqev7Luqpm3dDcvQlRzZJTFHS7FDyMt/KjyVsepawUru5ZSdCCy3r/xREq2mQcdWj72M1ZtozN01YSMk2httI3n5gt5SyntPaTyHPyZjw7tJqqa3ZZqcJfRH0lGq0l81XXpct/VnSNlU5dKojVOerKquZfxUTDgAXu8kqIJzjt44xGaqVOp10USZt6tyYmpF9IB7UEHKVJPJQOqSNQY1226BJUGmtUmjMhmXbGScaqPNaiOJMR5t32pposq/aFuzZRPFJFRm0KwZZJGqAocHCOOPWjvIj8/01Nur138B+ec9v1P0DXOrS6JK5eXYjik3PV9kO0+ZmbXqzVYMi+ZV7qiQ1UW86tLA9mDoCM7qwcZ1B6626WVb20HZuqdry00Kak5YzktPTICVyCt3KkuY4oPBafONQDEedFXYmxS5SW2hXtJJYm0t79Lp8wkBMo3jR9wHg4RwB9aDrhROI86TG1he0OqC27XeWq2ZZ0EOIJBqLwzhRHNocUg6Eje5Jj9IUXZNKPdd2fnM5KuDb7ehFVj1B9M4y1uqDb6d5bZ9gcZz/RG77Gbzp2zu8a2K4w+uUqMqWC8wN8sneKkqKeJBCsHGo00MYK36P6mp3lkLmF431cgPqR3RXsgnLDRcVQTtHlH5mTmmC0w8ErUlhwr8ZagjxwcAAKSPF8btjttgpwcZHjxcZzk12J6olZael26hSJ9Ljah4rzC8hXcfiMF00u0r4luouulpROBO41U5Qbj7Y5eNgkgHXB3k90aNV9ktftpCbj2XV9VepjuF9Sl1CnFpPkIbdAHkV2ZMWtB2kyLzpkLhYVSJ9tW4veSpLe92EHVs9x0744ZaLD3RPPlVZS91TyedQsK/Nn6jPWtOfNHQj4xS2neKePrmgc/zmz5QIvrY2hUSshDDy/AJ1WnVuqyhR7Er4eY4MbbJVuZklpekZkp3hnxTlKx5OB8sYa7bbtC+N52pSvqLV1/v+USAHD/rE4wrz6/ZCMlJriaz9TB21XvFiww2pvKVsUrozwmpf4ZqNSo696waECeCT/TGCvag7QrQtaeos9MeqVsTSmj4WhW+hCgtJTjJ32yVJSMHKddDkmMfbtDuq6KVKSiphElRZdBCHXPFSrBOTjOVHy4Ed3s57Mtc5Ozw8Y1JbuM9y/rNxSUsCzJ/25MZ3cIPiA+Xme4QU6ybjrqfD7mmjSKcMEBzAUftW+XlVr3RtFBZtu00j1JlRUqiNDOzIB3ftewfa+kx51OqTM+4Xpx8rI7ThKfIOAj03W58yNfWa4rX6mTk5AWzb3qjblvOsSLigyKnMo8d5ZBIAz4xGh1xuxkr4nrNlLaYak512eqKil2cqcwSBqg5aTnGmSNEjlxJjQbn2j1KpScjQpR92oNyqEtSzDaSGgUjAO6NVqxzhU6xJ6dR6s31VTTJNGvVFxIWB2Z1SgdwyfPHLiUms+Xp2/UzUFFZn5/uWV11SVvO/aYumhbTDTTbPWP4TkJWpal45DXAHGJFptkSE82pYrqm8ct1B/piJbqmbaeuSSNqy7rEk2G21lQIDiwr1wCvG4HBJ44jOKQhWpx6I0WxlNvDNeoreIpcIkg7OJDOtyLH/ho+VHojZpTVf4yufg0fKiL1Mt/UJ+9EVykmqamW5eVl+tfcO6hCUjKjGh02LlzObY15k4WdQ/mb6yWZrqp6WcO8GFISNxXNSSFHGeY88btSajuK8GcbDzLuUqQU5GvHQ6EY490RzZVvS9BlQhCEOzz2OtdSnUn6lPYke7xi62k3xI2BQ94dVM1yaTiVlycj7dX2A/4jp5PGvr6lmFyzChynZiBEG3K3ZDZ9f0pMWhVvBHFpE5Ly0ush6nLBwCk8kHXdB5BQwUx1Ds5qKdsexCUmL2oKAipNrZmWVIw2/uKwmYazqkKICkniCNCQATz30e9ldQ2r3HMXZd7k0/b7b5VMPOqwupvg6tg/5NPBRGmgQOBAlDpPbYmLWkl2FZbrTNW6oNzcxLjdTTmSNEIxoHSMYx60anUgR3bW9sE8teZ9bSnCvMmcwXjS02TtAqlFptWaqzVPmC0iZb/dE6HcXjTfHrVY0yNOwbFMXFLUxCUllUw+Rnq97AT5TGsUGmIaCJhxG6B+lox7pjNbwGvHyx69UHGPJ5OpcLJdjIMbQnW8BFCYVp/lj8mLtrau+xp8zcqo9hmFfJi42YTGNodDGBjwg50/1a4uNsbwVtGqWNNGuX+rTGbhldzj6VTntcC1+fJNJOlrSX4yr5EI7aZ/eCUWpJEk4AEyrJPZjcjXN+PFhvfvG3TnhUZU/wD7CI1Trwsm+vS6eUknBG0zW2SsSyczNnS8vkHd61xxGcccZQMxKLKHao1IvMpDfXMJdXjgneAOO+ML00GUretoAZ0nP/ajRrvvWan6bJWra7oHWS7TUxNB0Nb53RlCVKwEp7VE93l0RT7mrV6CuTjGpY9TKX/f07PTAsiwUPTLz5LT81LK8d0+yQ2rQAfVOZA7CBrG87Ntmtt21RtysyEhWqm8AXnJhhLjTX2DSVDQDt4nuGAMHs4p1oWZIEJrdJmKm8nExN+ENjTT6WjXIRoPKdTyA2pV00LP6+U38aR8cefqXOXux4NVk+lHpUx4Xn6mc+Z6yzxtG3/a9r4oqFr2QtKs2fb+d0/4Pa7PJGvKuyhJOtdpo/8AukfHFbV4W/gn5oKXwP77b7PLHJGizK5ZqhZblcMxewkrHRLq2+SpXV1HeJOpPViIGtY4pyuGOsPvCJ52GrSeilWAcpPV1Ef8AiBreATIKx/lD7wj3tOveZ7uq5ibxs3V+jukfxx/IVHv0nDm5KPoP1vX8IqLLZwoC+qR/HH8hUXPSVVm4qQf9gX8IqOqz4Dzq+L0dkbIB/ertf8AkqX+DEbTGrbIP2qrW/kqX+DEbSY+bl3Pql2CCCCIUIXKHCPDSADXzwQQQAQQQQAeaFDMECBCMEOCKOFD5QoECCCFEA4UEECj5QoIcUBAIIBEIwMGINYIAPNGOujS2ar9xP8AwaoyOcc4x10H9DNV1/eT3waoqIzgPo2nF5s/yOv32oyW1heb8n/I3+QmMT0czi8Gj/uhfvtRkNqqs33P/at/kCPpK/lo+dv/APJf4f8AJol35NNV/Fue9E99KArctOTA4B9nP3rmIgW50lVOUOB6tfvR0Rt6RKP2o+1OzSJZPgqFtOLOnWpVlIHMknTTtjmtXvpmF796tfV/8GI6QBbmOjhZL8uSZBBlysI4bqpRYT/TiOgG6yTSBIyxQJVag4lSfZJIBA8nCOeNi0/TL+2VT+zCuzRbm5ZBVKKOqwyFBbbiRzLSzgj6nd5GLyw78mbK3LJ2jodkJmTG5KT2FONOtA4T4wBJSOS8cMBWCDEhGL4kb9WrHHMP/kTl1wPPWNV2vPMp2XXMqYI3DTXUje5rVgIHl3iMd8ebt9WazJ+GOXZRRL8lidQc+QA5J7gMxGty16c2x1Rq0rUEwxbTDqXanVVoKckagBKscMgpSdSrBIATk7Wkjz9PTOUk2sYK7vLqehnSmpv9MUuU6kHs8KKkY/8AD9yIn2XzVgSjtX+b2TnJhLkqEU/qErVuueNvet4K9bhR0GDEkdJe6qepumWBSEJTLUvcemQg+K2oIKGmu8hJKj2ZHfjRtl1SsKlO1FV7W2utpdS34IA2lfVEFW9oVDGcp9Eaek5RPYlYksM1ywn6C1XZNV3tPu0wIV4QmX3t4q3dMbpBxvdkSYKhsExpS6x5/CflRefNbsJz4uzV8Dulm/zkaPtOrFk1WckFWXbztGZabWJoLSEh1RKd3ACjwAVr3xjZTvfLaNEnGx+aNybqGwMDKqVVPOmZ+XGDv+f2VvUBLdmSE8xVBMIJW8h4J6rB3vXqI7O+I8Cs90CiAmMY6dRedzLGpLzZP/RpeT6iujPGrJ/IRGi7dCn5+FZUDzb+BTGwdHSYU3T1p3jg1VP5CI1TbWsnbPWFZ9k38CmMox/ibjgqWNRNGEKwEkqOABrEvWPb8ja9GVXa280xMqb3nHHThMsg+xz2nTJHHhEU2+hD9eprLgCkLm2UqB4EFYyI3npGPvpo9Jl0uKDTsyta0g6KKU6Z9Jj0VwtxbIuc1XnubK3tUseRadmm6i/OzCEktMtyriSs8gCpIAJ7TwjSLEtS6tvW0R1+beclacxjw+cbGW5NrillnOhcPLTmVKHAHdNj/Rup997O6Tdcxd1QkFz6VqUwzKtqCN1xSdFK1OiecdLSVEo2yzZbOy1s09tuXpcm7MhLh8Z9xKCStxQ1UpRAyY8vU67d7se57Gi9mxq95kebaNo9v7ErKlLRs+UlG6yuX3adIoTlEq2SQZh3t1zgHVas8gojkKltv1ScdqdXmXpt15wuOvPrK3Jhw8VKJ4/98oylry9R2mX/ADU/ctRdmH3kmbnnc4UtIUAG0fUp8YAdgHbrGavxlpm65tmXbQy00ltCG0JwlKQ2nAAi6eKrljzObWatSl0omTsiUp76azVJ6VRON0uQL7cqskIcWTgb2OQwdO+Mm6xSU1O1aq3QpIsVtBZfkl7xZbX1qUdYgZyDg8OEatZ8xcErU3HqBKuTbvVFDzPUl1C21HGFp5jOIyS6ncVaqjE03Tt9VIUkNS8tLENS26rON0cNU6+SOvblnj2QlueGZ226ZSnNo9WoMxRJF+ULr6mi4k7zAQkkJTrjEY63jSqXZVMrE/R5eqv1Co+CqD5P0tsAesx7InJzFrRKnck1X5m5KRIGcmVb6ni3LqW2nfGugPZyzBaE9ckpTHpelUpFRk2HQ6Q/Kl5LDqU+vHDdVgRVD0MHGXqZmpSNKtmVuGeVTmar4HUkyUszNrUW0IKA4SccTrjPd5Y16/6YzS7kfakG1ty6pduZQ0pWer30bxTk9hjIWpMXVNOVF6RpQrzU2sOzrUxLB5or4hRBIAI0wByA0jBV+qT1TqE1N1FRVNO5SsFG7ukDATjljhiDh6mdSame2xzZi7tLZqM9ULhdkGpJ1DRwx1y1qUne0yoBIAjqDZrbFOsm1pK16U8/MMtOrcW+8Ehx5a1FSlK3dOwDsAAjmLYdtQptiSNRptWkZ9QnH0Oh1hKVdXuo3SFJJB9GY6Msy56dctJlK9SJlTsi84pKVrQUKCkqKVApOoII/wCxHJZFtnvRe1cHNG2CuvX1tkqy33VqkKa65IyreThDTKt1WOwqc3iSOIx2CPNkIaSENJShI4JSMARZ39TnLS2wV+RmwpDczMuTLSlaAtvrLiVeQEqT/NMe6CoxvrxtWDi1jlv+hZ3HIszUi48G09e2kqCseuHNJ7Y6N6OF4Tdx7J22p19b83RZlUiXVKJUtsJSpsknUkIUE557uecc71d9EtT3VKI33ElDaeZJicui7R3KNsmm6hMhTfqxUFPS4UMFTSUJbCvIdxRHaMHnGF6yuTZpJPY8lG03YxSb2uSZuGXrkzSp+ZShLrYl0OMuLSkJCyMhQJAAOvKIAorMxTq7VKO891pkn3ZdRGd0qbdKCoA8AcGOjL22sWtZ9VXTp01Cbn20JcWxKMg7u9qAVqITnGuM6ZEc30+eNTuis1ZLZaROTL8zuE53OtdKwknmRnHmiVo2Xc1vJnSvU6xvWzWgNzKE1uoJCmkqPg7awN0lPFw9oBzgdoz2RHbilYJESNfDrkpsVe8GV1ZMkw3lOhwtSEq9IJ9MTUSaSivM8e6OdsF5mbG1KwWphSZivpdCDr1Ms64lR7lBOCO8HWIzuap3NtqvmTt+3JJa0lR8ClFK3UNJGiph4jQYBGTrgHdTknW/6OexWV2rSFYmpq4ZykimzCGUpl2EOdYFICskq4dkdd7Fdk1t7LaS+xSlPTs/NkGbqMylPXOgetR4oASgckjmSTknMcEnXS3jmR7mi9kwramjUxL2V0atkmSrwucdVxwBMVSbKeHckAeRKR6eL7juK4b3uqauS45kvTs0QFqSCG2kJ4NNgk7qRnQd5J1Jjedr9cre0rbxPUmdnUMlmpvUinpO8pmWbbWpJUE/VK3SpXMnAzgDGU230Cl25J2xSKS11UuyxM6n1ziipreWo81E8T8USu+FN8KpfFLk9O2mdunnbH4Y8GiybiEIS2gBKQNAI3ZSOssCSWn9zmyD6V/HGgS2QoaxvNDf8IsmoygOVsOdckeg/wBBj6Grl8nyuqjwmiUrMdzsamkg5LM9lQ7t5s+8YiXZ3dtIs7b5U6zcEy5KyBanJdTyGFulCndwpJSgE405CJH2LP8Aqrb1dt7I6x5rrWgTxON33wn0xgja1tV9XWVOlt9e5659slt0nHMjj54kqXbFxRwaHUx0l896Jytm4KHc8ut+3K/TquhsZcEs8CtH2yD4yeXECPC6KO9VLSuGUY8d95pS2kj2SgkKA9KcRzVKTUtse20UuoSjz0zIhCC6DhTqpZ7KHEkJHjEEbwAGTupjpwVU02suy5VhAVjPdxBjglCcZNI9qx1zgp+TNY6N9bk5mUqlFLxU88kTCE5zvN7oQojyEjPlEe9XTNU+aMlMoKHm9NeCh9UO0GNLv20q1atyfNXaPXokFOiYUmXKgZZed4ghOCponlwGcHTESHTtq9uVdG7c1ASywQC2sYmRnn4uAR3EZjVNb5bkso8zUaONlcYSlta7ehiKZLzVWn0SMokqdc4nkgc1HsAj06UFVkpOi0miImMKbCn1oB4NpTup3v6PIYvaltftmi76KBb2+yEk75UiXBVjTxQCSM9usaJs6s2rXxdK7zupkoo65gzG44CPDXM5CUpOvVDTU6EAAZGYwlPptSawl2Xqb9Ho1CqVcJZb7vySJEp9IdoWy6jU+ZBTMJYa6xP1KlZcUPNmMFcFQo1Al2pi47hp1IQ6nebS+59MWPsUDxleYGNhrlaTcFyM05pzMulR3lA+u+qPuY9Mc4Vp2T2r7cZ4vPOtU5ptbTZRhLnUMaADI0ytRVwzgnSOytTwk+7OhRrWZeSLfaPdFGu7bRRKjQJl2bkmpeSlOtcYW0VLbdcKsJUAcYUNcRMNzt9XsSSM6zFRBT5nCf8AkMakq1rXt0h2m0pkPtZKX15ccB7irgfJGx7X5sUq1KBbpVh1CC+6ByIGPfUr0R1qt1xSZ5Or1MNTdHZ5EcNlTFjVJR4LmAB6UCNNedynMbtX91ixJJg6Lmni6fJqfkxoL+RwhZxg9DTLOWXNGpc7XavL0qQSkzEwrdSVetQOJUruAyfcicBULS2X0SVkJyoJlg8SreLanHplegU4UoBJ5DPAaCNA6PSUrvqcWtAJbpi909mXW8xrm21TlQ2tz8tvjKVS0m0VcEpKU4HkysnzmPjPacZe0tf4OUsQisvHmfeeybI+zNB4yMczk8LPkSHe+2ukN2+ZWzZlcxUZjIVMuS62xKp5qAWkby+wcBxPDBy/RX2HCtvsX/eMosyCHOtpknMp3jNr4+EuZySnOSkK1UfGOmM7ba/RItim1yXn63clRrsoysLVILl22WnscErIySntTkZ4HTIOzdL+76tZ2yVliguJknKpNppy3miULZZLa1K6sjG6cI3QeQOnKN+k0tGlj0dOu/dvuaNZq7tVPrah9vJEQ9KvbO7X5uYsCz5pRpDa+rqU6ws7044CQZdGP3MHAUR64+LwBzEdvU7wJAfeAMwoYx9QOwd/bG57BraprlMVdEwhDjrZdYlGd3xGd0YK/tuQ7BGssqBYax9Qn3hHuaeMY5jHyPktXrOrNwXkXrLgKwT2xb7GV2K5V6vS76TLtszraESUw9lHUuJUrew4P0skEanAOMHlHnv4GcRZ2RRZC6drUvQaml7wSaDm+WV7qwQySCD2gjsPfDVtQqk5PGC6Gp2T2R8yRahYV+bOZv1Y2cVyaq1PVq5JOKSVKSfZKbyEO/bJAV2DjFi/e9hbRkGQvmlIt6up+lCdTlGCOXWEZR9o4MA8zGuUap35Yd8Vq1LZfnLilKSVOOyjrZWCykIy4lAO8gjfSCEdud08tyZqGzbaq2lqrSwo9fWjCXNEPEjkl3G66NT4qte4Rx0amaSb95f/AHc36imVT/iL9Ua1P2jfFjOeE0N81yjkbxSkZwO0t5yPtkecRmLbvOlVcJadWJKcOnVOq8VR+xVwPkODHg/Sb92ZrUulTCq1RE6qbAUpKB3t53mz3pyO2LZ6dsXaCkb+7Ray4M5GB1h8uiXPPhUejCNdqzFnm3Vq1Zks/VG0bRlKVsTrqCCQJpjzfTmo1WlKPzA0RJz6w5HpjE3Izelu21PUCafVP0KYKFKcx1gRuqCgQT4yPWjQ6Y4RZUmm3XctMlKcgmSpbCMJcUkoCh5PXK49wjPSVOlyz5mUK0qlHPGSus3NTpAKbZUJp8abqD4o7ir+gZgpVsXHcn9s1yYNIpo8bdUMFQ7QjPuq9EXKnrOsgESiPVirt8XFYIbP22N1HkGVdsebdHvO93Eu1d5dLph1S3ulIV5G85V5VadkbLLMfG/0OhbYrK4Xq/8AhF581dqWqgSNmU5FTqK/pZm1gqKj9sBlfkTgRXK2dcl1v+ql6VR6Rlh4yWd4byR3J9a2O85PbFRqNm2Ogy1HlTU6vjcK0neXk8isDTX2KRnujHtSl0XjtBptp3S/OUUTmF+Dpb3erbKFLSrcJ1JCdCvUdnKOO7VKMW5cJcmyjT2XS/hLGfN9zG3gm3EXPIy9sdUZJhDba1t5UFudYSTvH15xu68IyyzgxjLnpUhQdqlVodPQsSki51bIdVvq/SkKySeeSYvN8nlGdE42QU49mYaup1T6cu6PQuY1PCJRtqm0y1KIusVt5qWfUkda66dGUng2O888ak6cojq2EpduWmtuJ3kmabyDz8bMZfpETDnUUaW3z1S3HXFJzxUAkA+hR9MatRJykoHnSh1LFX5M2qe2r2jTadMTVPml1GeSjDEuJd1AUTyKlJAA5k8eyNF2S2Bce22/Zmp1uYmE0dhYNUqCPF1ABTLNDPikg8s7qdeJGd92S9G2QvWwqLdU3d9Rkk1FgPKlmJVs7gydAtRPIcSI6Lq8jTdluxiqJtWnsMMUSmvPy7SwSFuJSVbyzxUpStSeJJjilKuD2w7s+i0Ps1UJyIw2+bV6ZsotuWsqy2JRqtql0ty7DSPpdNl8EBwjhvaYSnt8Y6DXkumS6phxc5OrdeUtRcUt5RUt5Z1KlE6nOc5PHMbJs5oZvq9KhU7mnnp5aSJqdU4crm3FHABPJOnAaAAAYEeu0RaBfNWQ2gIQl1KUpSMBIDaMADsj1NNp+nHczn1OoU57EYtTgznMUrXmLcLGYM69kdOTmSSNm2YEq2jUMf7Qfg1xe7YQRtGqWexr4NMWWyo/3xqJ3TCvg1xd7ZF52i1M7w4NDj/q0wx7pok11f0NVzyMVSJHzX28Tpioy3w6IzsjZlXqVpy9wUrE4FqcS7LJGHEbiynKdfGGADjj5Y1Vl5SLroSFBSVJqUuFJIwQQ+jII5GMLOI8nRQ1Oawyb+l0gzdXtSUbflWS6ZtPWTLyWWkZLXjKWrRKRzPoBOkV2vQdglJorEpVbltitToBU/Nv1FA31HiEpCsJSOAHHtJOTFt0lUtzV32czMNJdZW5NBaFcFD6VFrb2zCUrdKcqstS6EzJtP8Ag6lzcwGvpm6FYGe4+/GiMPcy3hHQ7VF4xlmxuSvR1/hNme2Cflx4KkujsTkTNm+2CflxjWdkjbtfm6G7b9IlpyUlfDHC+6EtlnIAWFjIIz7xi2f2WySKvKUuVo1FqU5NhRabkXkvet47xyAnzw6UG8bkTxGFnazPIkOjqrRUzZfnqCflxX6m9HMDSaskf/kUfLjA3BsplKLT/VCapFCflkuhlxcrMpd6pw8EqGc58mYsq/YFJoFWfpVSodPRMsAb4R4ydUgjB8hEWNCn8LRJatQ7xZJ0wm05bY7X2bLXIKpHgU2UmRdDjRcKDv8AjAnXhmOVKA5/aR19mfeETpseQB0ZKyOe7USfvYgWi+LKYB9n/QIxqWJGV3MTd9nS/wBHNJP+uV+QqLzpHEG4KSf9gX8IYxeztZ+bela/uyvyFRf9IdZNdpZz+8V/CGOufyjggsahHaWyH9qy1/5Kl/gxG0Rq2yHHzrLX/kqX+DTG0x81LufVLsEEEEQodkKHx1gECAOcGkAhGIAgggMAEKCCACA98OEYoKuUUxV7sU84AIIIIFCCCHEAofmhc4cCBBpCgijA8woIIFCMddH7Gqr9xPfBqjIxjro/YzVfuJ74NUVEZ8/ejwcXa0f90q99qL7aqr9HU8fsW/yBGP6PxxdDZ/3Sr32oudqq/wBHE6fsG/yBH0kOKUfO3f8AlP8AD/k1KskuS6W+G8lQz2aRMNsW7Xdu91LqlTW7RbRpqeqdmWyMN4x9Lbzop05yVYISNOwHUdj+zqZ2k154Tc4um29T0hc/OIICxng03n2ahk5wQkDtIjoi6blt+1LUSxLMN0a2qYncl5VlOOsUTp4vslqJz25JJ5mOOyTk8ROjbGOG+X5EX7eLOt62HJW8bFeFtLlFtMMy7St0vLH7ojiSvGSsHIUkEnnmykNrduXBTk03aFbrD/VnIfaYDzROPXbh8ZtXH1pPm4Rqrb9Y2n3Ka3W9+VpTH0tqXbdJS2OPVoPNR9kvGvoA3+cpNGnpdtiapUk6hpIQ2C0MoSOAB4gd0dVOmcoHJqdZGqW2XLMOJjo/tu+F9R1i+PVFibUPJukYjxre1pQlE21syoHgLZBSh5DCUKRniW2U6A6+vVz5c4uzZdrhe8KS2cci4oj0ZjKyEhIU1otSElLyqDxDTYTnykamNq0b82c79p1pcJsjSsWiKJYk5U6o6ZirvvNalZX1QKwVeMfXLPNX9ZNOy65LToIrAum1EV8TkoG5QqCCZdwb2T43rc5HjJ8YbugOYkC5KWxW6U9Tpl1bTbu6d5GMpIOQRnSNQZ2YyYHjVyaPkYT8cS3Tt8JcFo10JRzY+THbNrgtOhy80i67WbuBbiWwy4pKD1ZAO9oojGdDpG0vX1slXqNlbB/8Fn44xo2Z0/8Az3N/gE/HHonZlIDjW5v8An44556B2PL/ANzN6zTt53f7mm3zUaHV6+mctyhpokgJZDZlUpSkFwKUVLwk41BSP5sYQjSJP+dlTyP17mvwCfjgGy+RPCtzX4BHxxnHSTisGxe0KfUvdgZ3JFXP+6aT/wAKI1bbM5/fiqx72/gkxJ9g24zQ+okpIuvgP9c664NSdNdNAMADERXtgcbf2s1dbZCghaEE94bSDFtq2JGjSzVmonJdsHjajifmmpX3az8II3TpFOBUlRu51z3kxoNsqIuWlfdrP5Yjc+kCsmRo+T+6ufkpjb/6mbcY1ETqzoo5+h/tfX9xd+GXG1bW9Nl9zHP+Cpj4MxqvRQ/aAtf+Jd+GXG07Xz/etuf+Spj4Mx8xL5j/ABPqYfLRwv0fdbontP8AB3/uIi82hE/NjPDH1H5CYsej5k3TOn/dx+ERF/tG0u+dx9h+QmPVq+cz46z/AMt/gXGy9xaL9pCUOuNhb+6sJUQFDdUcHHEZ7YvLEdeTtGnW0uOBtZnStAUQlRAXjI4HzxgLdpap9Uw+qdTIy8o31j0woElGTgABOpJ7oyMtbKn6+3TvVuXZ8JaS7KTHVrUJkKzkDGoIwc5Mego8GM1Hc8szVmsVSdsu2U0FTm9LVBS58NO7hQd8EKXqMp3PL2RlLdnWF7RLpTITBMi5JzjgQhf0tShuDexwJznXvjRqHQnZ6SE16rMSCHp1Mi2FhZLrhwceLyweenkj0nrfXTpOYm/VmV3JWfEhNbiFjqskjePaMDOBmHYxdUW+5tNAFVndndKlbdU8ZyWqynJpLLu4pOQNxatRlIGI13adMy01f1YdlFIU0X8byOBISkK93MAtibTcTFKlasypD0gJ5U4kKbQhjXJIznGg07xAbUZRPU1Ar0n6mVJCjKz4YXuFYIT1ZR64Kyca9/ZEaciwUIPOTSK8pkSalONBaz4rZxqD25idOjhJVKnbOHXZ0lLVSnVTMoyeKWt0I3+4LKcgdmDziJbuoCpOpzdKW8l1+TdKAsDdCyB2co23ZltTZt+iqodzszbzUmgiSeZG85ujgwoE/eq4AaHgDGicGelVYpRwiXr9sag7RKW1LVVwyFVlgRJ1FCQVJB4oUD65J5pPlBBiGazsa2nUZ4y9LRJVWWzhDrE423p3peKSnyAmLmU28zYqK1z9vS/qcs4S3LPHrmh9sobrh7sJiW6VVk1WlylRkJl/wWbZQ+z4xTlKhkZGdDGuKkmbJ/DyskdWXsLnHZpFR2h1eXbl0nJkZV4rW6PqVOYG6OOQjJ7CImSfn2FBpiVbSxKMICGWkAJCUjTQDhppiIt2k7QJS1JlNPTLvVCrOS6X0NqXutpQpSgCtep9idAM8OGY1O2NsrPVPNXTIusvNpKm3ZFBUl08myknKFdiskduOeTjnlhbmsJGn7SJCZpe1OpCtlMyJx9U006U+K404T1Zx2JxufzYrSEITuoQlCexIAEYmt1mrXtci61VgltpKQ20w2o7jLYJIbRnjqSSrmSTpwGS3zjWM4co1ajv3PQkY1iQ9pH7S7mP4NK/CNxGql6HlpEkbQiVbG1/csr+W3HPqe8TgnxbD8Tff7H5kUK7vu9n4IR1GeEcu/2P39Y7u+7mfghHUceVqfms+y0/y0fO1hIT0oJr/wCq5z4V2Ns6Sy8VS3wMasTH5TUakgn6J+b/APqqc+FcjaOkz+utv/c8z+U3HLcv8Xo/KzppX+D3/mRF7S/Gjbtn84hms+DvYLM0gtqB7eI/pHnjSmiRF7LzC21BTailQ1BB1HfH10HteT5C6vdHBJtkVT5jrybW6pXVsrLTh5qaVz9GD5RG43uEUWuvTjSVOSUyhUyz1QzvaZUkd+dR3KERnVHFV2jtVqVSTMy6dyaQnjga583HyHujd7CqsvXqALdqjwRMteNJOniMexz2j3Rpyjqi/e4PC1FW1qz9zQ9hzbN4bUZu4668xMzsg14dKSCj+nOg4QU50KGhg445KTyJibpdc3NzRUQt19w5PaTEIXrak9Rax6uUFT0lPyznWqTLnC21D90b7Qeadc5OhBIjITu2G765IN0egUlin1WZGJibkMqeePa2CMNDtOTjkRHJKucG8+Z7SnXqIqUXwvI6EZqk7RkJYqEssN+xVnh5CPejGSNv2LWZyZfroQwSMoDbi2d5ROp8XA4e/EAsVzans0lA9NumfpLqk9Y3OTHhjCVq9jkq3kK05HdJPMxK1ErspcFp0e4pSVRKCfZUXWELKktupVurSD3KBEcdmlVk1ltNehvVirre1KUX6m1U+3dmdJdDyJBmeWlWUiYUuYA7NFEjPljJVa4J2vNqk6WwpLOMKUDjI7M8B5BrGhVeqy1GtetXDMyjc2mnS3WIZWvdS4snCUk68TgeeIkfuXadtEYcNOUadS2VHDci/wCCNFYwQjfyFLVrwzjhnEZx01cJ8LLMVOcq/eaUf2JgcXNSE8l1tKm32lAhJGPNiIg22sNWbtGkbmokyzKT0+gzkxT/AGTKzopasabjmumhyFHXlkadtiuihSjtNuSiS9RqsugiVmpzLbrRPAuADDg46gjOOJ1MYqzrTqdz1v1cr6nZ+em3N9CZg5Lh+rXySkck4AGBgYwI6tsrMJI15roi5SfDJa2fJFyVuWnH21NSTDaZp4Oex0ylB8+vkSY0zaBVTeF6uOSiz1bygywr6lpOfG9G8rzxndoVXl7ZoKrXo75XMvjM/MJ0JzxHlPDuT5Y0ahvGjUx6tTST1zyerlkn6k8/5xHoHfG+TzLk8bT1ZbsS/A8doVQQurpk2DhmUbDaRyzz9zdHmjU3XARmKpp5brinHVFa1ElSjxJ5mLVRjnlLLye1VXtjgkzo6pBvSofyar4VuNV2r+LttnP5Rk/eajZ+jgr9GtQGf8GK+FbjWNrX7dc6f94ynvNR8nFf4zZ+U+wf8mr/ADM+jY8kc5dPkA7NaD/LafgHY6NPHhHOPT5P97agD/fafgHY6dP8xHNqPlMjDYcrd2cJH+0TOnniOJZxXUNY+oT70SFsVJGzoD/XzERxL4DDX2g96PW0/wAUj4xc32fiXO8SNdBGOnKW4qcFQkJt6VnEkFK23CgpIGMpUnBSfJF6FY7Ye/5Y6ZRUlhm+EpQeYmQ2a3s5am1Rd2XQ3Nzrk5LLl5pxASHPGU0etwMBWA0AQNTnPHjebNLPou0GbvUzb8ywqXV4ZIzLJwUhbjyjvIOigQlOQdRyIMYF5Db7RbebDiTyUMxi0ylTpc2J6g1GblXwCPpLxbXg6EZB8YdxjzdRoM7pUvbJ4/0PW03tBPEbllLP+psFhX9e9LttNXXT5qtW+ysNPOuLKjLrKQrd6zVSQAQfGG7yyI2N+k2LtHbXNUh0UyrevcQhsIWT2rb4LH2SfTGqWRd8rb+zu6rLnKe+DV2XDLvtn9LcLQbCFJPBPig7wzz05xfMWdTFbB0X8w/NStZlJ5baltPEJcSZoMpBHFJAVkFOM41zmNHUdc31FjlJP1M7PZ9dq36eWHjLK5t+97GZLFRbFUpWd1t5aytGvAb3rk+RQx2RbsOXleqgmX/udTCdVpJQgjsz65fkGkWlTu+vztnOUirtCZlpvcLU4vRzxFg6kaK9bjXB56xj3bnr4thiQkd6UkZVAaW+ySFryT7LlxxhPpj11OxRwzyowk/Jbjd2JSx7FCVzbgqdVSMpSUhS0n7FPrUDvOvfGBvuuXhP0JmpzMi/SKNOLKJbd8XryBk5Oi1JxzwEnvii57QptL2I0e7G3Jh+q1eYbKlurwlCVIWShKRx1SDvHJ8nCLnalfkjd9KoVDpcnNKRTWkhb7ox1i+rCSlKOOAQdTjyc48xaud0l0llZab9MHqR9mQ0+Z3yzLCa/Uy1/WrQtl+0ezEy0xNLlmdycnpl7K1uFD2qghIwNBgJSPScmNbv275u5dpb10Wyiep7qWkMsOBQDqQlBQV5HrchR55HljGuy1Tq085UbgqU3OTLhytTzxccVrnBUeA14DQcsRkGkNMoDbLYQgckjEbaPZ+Ns7XmSWCaj2l3jUsJvJjqZS1y7xmZl9b0yoHeUVFXHiSTqo95jKBRGhinfB7YpzmPQjBRWEeTOUpvMjMWkr9FNM+6Ue/GR6RCsqohP+v/APbjE2nkXPTeH6qR78ZHpCkn1E8r3/JHJd81HPBf9zE606MJ/vB2hj+AJ98xlNu5Pzlry1/wLNfBmMR0XSTsBtDn/aI/KMZTb2cbFbyOcYos18GY8x/M/U+z7QONuj3k1as64/tZr8tUYfaFn5uauf8AXD8hMZTo/LxVawf9Q1+WqMVtBOb2qx/1w/ITH0sVmpHy0v8AyH+BhARngYYI7I8lK74W/wB8azfjJm7WrJoVwSVXTLCZVKuFfVKXu7/ilOM4OOPZEjfPumjoLYZ1/wBuPyIh4L1xDDmDGSlg1SojJ5Z0NLbQqV8yEvX6qhMo7MKcS1JtL61xZQspynQdnE4A7Yg66rgduXaPRKm5Iy0mTPyqAhkZJAfRgrVpvq78dgjFqdUrieGkUyQ37soIOv8AdKVH/nojG6W6ODLSaeNVmUTZ0jHh819nHn1k1j/y4zlr1+2ZXZVM0+vyQqinK4h3wFubLLwb6oAujGpA1GNASeIijbbZVzXNVaJO24xJurp6ny54S+GwCrcxx4+tMaaNnu1rlJ2955qNS2OG2RslGed0SYZWvUdzaJXl+rNuGmm3ESFKMy6DKqRvApacyclWd7eHZjSLOj1Gi0G82Z2bnbXalJ2mvyDjluo8SWKikh1SU672mMjl5Iis7PtrfKUt78bgFhbWh+9bfz91RgqavvMN24XC9TeKhRbYoVlVJBrtFq9ZccZFO8AdUooQFDfKgNE+LvceHCMbtaqdPmb7qcxR35d+SWUdU4wreQcNpBwR3gxraLG2sg6ydvfjUNez7ay7wk7e1/2uN1eyD3OTbNU65zW3CSMnsafKujXWQR7GofkiILpCh4L/ADo6QtKz6tZ+wet0esJYRNhieeKWXesSEqRprga6RzVS95Mtgj2UaofEdc+UzcdnqsXtSv41X5Cov+kErNbpf3Ev8sxi9niv0aUv+NV+QqMlt7Oa3TT2Sa/yzHXL5LOFL/uF+B2zsh/astf+S5f4NMbTGrbIh/estf8AkqX+DTG0x8xLufTrsBheaGeELMQAfJC80EEAPPdBmFBAoHjBBBABDhQQA4RhiERBAqMUxUeEUwIOFDgiAXOCHBFAoIIIhQgghxQKCHBAghGOugE2zVgNT4E/j8GqMlFLraHW1NupCkLBSpJ4EHQiCDPnVsD0uZrvpSseluPfayncveczpvNtHzbgi1Eu/su2pTFFqXWbtKmVyq141clyMIc045QUK055HKNu2l24/XAzV6SlMxMIbCFtpI+nN8UqSeBIyfKPJH01L6lPB87qMw1OZdmaxsz2hT1kCckVSHh9NnHEuuNhzq1pcSMBSTgg6YBB/wD547aDeFVvSpImJxsy8oyMS8m0sltvPFROBvLPDewNNBjXOJdl5hhwtzEu80scUrQUn0EQsK7D6I0qtnRvjnJt8ntQrcjJNSUjRaTLyzKd1tttlYAHpi5RtduZI0ptO/BL+VGkg9gPohEnsPojYpTSxk53VTJ5aRvQ2wXR/m2m/gl/KhHa/dJ/wZTfwS/lRo2e4+iDe7j6Iu6fqToUeiN3O125z/gym/gl/Kg+e9dA19TKZ+CX8qNJyMcDCJ7j6Ibp+pOhR91G7/PfurlTaZ+BX8qH8+G6gP1tpn4Ffyo0ck9h9EGT2H0RMz9S+Ho+6jeRthun/NtM/Ar+VFaNsd1D/B1M/BL+VGhgnPA+iAqI5H0QzP1L0KPRG9TW167piWWywxJSi1DAdaZJUnvG8SAe/EaIltW+p1xa3HVklSlKKiSeJJOpJ7Ye8QOB9EVNlS1BKG1qJ4AJJJg8vuZRjCv4S+tjeVc9KSBk+GNH0LB/ojctvq0qlKOjOvWOnHmT8ce+zCzZs1FqtVKXWwhoEy7LgwtayMbxHEAZPHUmNX2yVL1VuhEnTwuZbkkeDtJaBUXX1K1SkDiSd1IA4kRsn7lLyaofxNQtvkdqdFNJRsBtbI4y61el1ZjaNrSFObMbnSkEqNKmMAfxZj12WW+q0tnNv224QpynU9mXcOBqtKRvHTvzGcqcszPU+YkXwVMzDSmnAPqVAg+4Y+XbzNs+pUcQwfPPYKtLdzzozqacSPwjce+0V/8ARfOd4QR94mMJQpef2c7SXqTXQULpzq5CcIHrkaYcA7CNxY7j2xIW0O1Xqghqq04JfmG0BK0JI+mo4gpPAkZ84j1oySsUvJnx2qSo1WZeZqls1GTl5efkag441LzjSU9a2jeLaknKTu8xGUZuClsXTRX0KeNPpjQa6wt+OvRWVbvlI0jTHesZWUOsutqHFK0FJ92BKir2JPmMd6t4wZuuDecmwUerybFPkZaZcdbVLVhE8SlveCkAAEeXT3Y9qtW5Gdo9dlWy6HZ6sCcZCkYHVjPE8jw0jXEpP1KvQYYSocEK9BidQbK0bvLXHSUV+TfcL6pNdBTS5spRhaFEklSQeONPLkx5z9ZpLLFvUqnTD0xJ0uY692ZcZ6tTilOBSsI4gAZjTTvfUq9Binx9Ruq9EFZgwdUH5mwXnU5apXPUqhJqUpiYmFONlSSklJxxB4Rrc4yzMkKdQFEc/wCiPTx/qVeiDdX9Sr0RHJM2w2w7MsalK9ZIqbaTjcwpKUjs7PNG3WftSrNu29J0VNEkp1uUQW23Xi4le5kkA7pxpnA7hGAAVjO6r0QfTOQV6Iw2xNyuWMDuGsz11XauuT0shhSkoT1aAdxtKE4SkE69/njymZRiYwXWwpXbwMemV54K9EBK88FfexeDGVuXnIIQltAShISkcAOUVb/LnFPj5zuq9EBQ4ogbqiezBi5Rrcl6gpR3VEnAwYkzaCC3sfcQvQiVlh599uNSta1Z6qTiFzku6xT0qy4pxO6XB9SAdde3hGV25V9hulMW80tJfdcS++lPBDac7oPlOuOxPkjkve6aSOdtWXRjHnBLP9j/AAfUO7lYOPD2Rnv6kR1CYg7oV2tMUDZAmpzrK2ZmvTa58IXxSzuhtr0pQFfzonE5jyb5KVjaPtKU1Wkz53Ix9E9Nn/5qnPhXI2TpMEeq9vDj/a0z+U3GtJBHSfnP/qqc+FcjYek2oJrVtknjLzP5TUc9v82o/Kzoo/k9/wCZEVAnexiPdojyR4A65hhRBj6o+VNltutPUiYU6yQULTurQdQe/wAoi68JLCw/JqKUZyndOCiNVbc7TF/JzimTpqk8UmNkbGuDmsoT5JKp1zt1VhLFVc3JhPrZjt8sekuZSiTLipZmVQ5MeMt1lICl+X/vER517avGZO79jFyzOuDAUo92THQr+OThlo8Zx2N4ul31ftWoUsjfU8yS2Ps0neT7oEabYV/1a07aRQHbZaqTDT7jzSn3HGlN7+CpOADkZyfPF5K1JSMHe1jZbSeerdekqS24AuZc3cqONACT7gMYzjGx7m8GVVktNBwxlGq3vtCql02q9brVrs02XmHm3XlsrccUvq1bwTggYG8AfNGx2k4ijWlT6fgoWlvfdSRrvrJUr34dzzL1Hrc5Sn3wpyWc3CUEkHQEe4RGAmaiFj10SCjW8pi2yWogo4wu5srrbFcdSX2pRYljvJcfSFFvyZ1/ojwqV2tUdtTFHcK3z6+YOvojT3pteqUKXqNcHGYtFKZQoOPneSPYcjFldxwWOmz8TykZNh4zQXOT61lk+MSpRy4fL/TFlcNZeqjyFOkbjYwhIGB5cdsWFRqLk0oBXioT61I4CMepzsMaHNvg7IUpPOD0dWOIOI8VK3jxhHJhZAjA6UiTejf+zeog/wCayf8Azm41ra0f79U8f94ynvNRsHRtc3r8quNcUo/DNxru1kE7aJ7+UJQ+41HysX/jFn5UfVSX+DV/mZ9H45z6eyFHZpQVAaJracnysOx0ZEWdKi05q79jNWk6e2p2oSSkVCVQkZK1NHKkDvUgrSO8xvpltmmc10XKto5s2KnNgBCdT4S+nznHxxHMurMu3j6ge9Gc2GXGwhb1Dcc3fCVeESqidFKwAUjvIAI7cGL287WnJOednqdLqek3VFZQ0nKmieIwNd3PAjhwj16ZKM2n5nxUv4Wpkp8ZNaBOIMmKPpgOC2sHvSYMrz61XoMdeUb8oryYe8Y88rx61XogyvOiFHzQyhmPqUzMsxMp3X2wrHA8CPIYx78vUpSTmZOTnplcjMgB+WDhCHMKCgVI9aSClJBxkYjJEr+oV6Ipyv6lf3sYyUJdzbXe4PhlVCm3BSW5Z5sLaAUktuJ0xkxTc86t2keBstJQ0pxOEITqcaiDxvqV+gwxv/Ur9Bhx6mKcd24xaJSqVFiVZqc9NKlpRoNS7DjpUGkDgEp9an0ZjJysszKoCWWwntPM+UxVlYPrVeiDK+xXoiQjGKwjOy92PlnoTC3j2xRlXYr72Flf1KvvTGzKNOYlfLjBvYHGPIqX2K+9MVtB51YQhpxajwCUEk+iG5FykZe0fHuqmJGT/bKT6NT70ZXpAgKFFTnXLxx95Gb2dWnNSkyKvUmi06ElMuwfXJzxWrsONAO85jRNqVUmLmvJqnUNtU6tvdkpJtvXr31Kx4vcVFKc8MJzwjhnJSsz5I0ad9bVLZ5HaPRfQpGwK0ARjMgCO8FRwfRGU27tlexe8kgamizIH4MxsNkUJi2LNo9uy+Oqpsm1LJxwO4kDPuRc1+QZq9FnaU/+kzcuthemcBSSnOOfGPKcszyfZuPu4OANhLgRVqqnIyZdv8s/HGJv5ZF6VXXi8PyExb2d4dYu0F6l3Cky70otdPqAJOEEEeP3pyEqB+pVnnG67S7SmZ10Vilo657cSl9pOMrSOC09pxoRzAGI+npe+jg+WtXT1D3eZGucwu+PN0uNOFDrbjahxStBBHmMG+ez3IxwzfwV574CYo3j/wBiAH/vETDG5epXnywbzzM1LTksQHpd1LrZ08VSVBSTrxwQIpz3H0Qb2vOGGyqST7m5fPZ2l/5+/wD1WPkRSraztLP+Hz+KsfIjUAruPohEnsPojDpobl6m2naxtM/z+fxVj5EL56+0v/P/AP8AqMfIjUideHuQsnPP0Q6ZdyNt+ertJ4mvf/qMfIitG1naUk6V7T7kY+TGoZPYfRBk59afRF6Zd0Tbp7antDn5B+QnK11svMNqadR4MyN5KhgjITkaRqLCShrdPEnOOyDOvA48kVNb7qw20044s8EoQVE+YQUceQc16mw7PEqVelM3c6OKPm3FRk9u6ga1TxkZEmo+bfPxRntldtTEi8ur1NssvqQUMMq9chJxlauwnGAOQzmNMvUzF97QW6VQB4Q9Nrbpsju5IUSSCv7UFSlE/UpzG+33KOTlq/i6jjyO8tkyVI2X2ylQwRS5fI/8NMbOIt6ZJNU2mytPY/SZZlDKPIlISPei4j5d8s+mXYR4woZ4wohQgghwAhBDggQUPnBBAChwofOBRQcu2CA8IoKtMQjD5QogCCCFEIGkEHKHFKA4QQQRCBBzg07IOXAQAeeH5IXmhQGBwQoIoOWunda9JblKBeDLJbqr016nPKTgB1rq1uJ3u1SSkgHsUR2RAtn3xUbfZTJuMiekQfFaWvCm/tFa6dx08kdK9PH9r629f8Nf/wCu7HII45j1dHNxhlM83WQjKWJIl5radQlpCnJafQo8QW0q93ej1+eVbmNWp78CPjiHs90PMeh4uZ53g6yYDtLtvm1PfgR8cHzy7bPFqe/AD44hw+SPIvta/TW/vhDxcx4Gtk0fPLtv/Jz34AfHB88u2v8AJz/4AfHEMB5vd3t9GM8cjEVJcaUcBxBJOPXCC1cy+ArJl+eZbX+TnvwA+OD55ltceqnvwA+OIaU42FYLiAe9QhpcQs4SpKvIcw8XMeBrJk+eXbP+SnvwI+OD55dtZ/Sp78CPjiGXXmWlhLjraFHgFLAJ9MVKUlIypQSO84ieLmPAwJk+eVbeP0qf/Aj44R2l23j9KnvwI+OIbUtKRkkAcc8oqQUrGRgjti+LmTwNZMXzy7a/yc8f/AHxxSvaZboTlLFQUewNJGf+KIhIg7oeKsJ4Ko3m5dptUnpdyTpDCqcwsYU8XMvKHPBGifNk98bp0LrdplwbXHJuqNB4UWQM5KskAo64rShKz9qCSB2kHkIhAnOkdCdA0Y2nV0/7m/8AeRHHq7Jyg22d+kqhCaUUdoK1hJ8UwuUVHhHiHtHLHTttKky0lSr9lkqZqj0yimzISBuPo3FqQpQ+qTu4B5g4PAY5+tLaBVaHLpkZhr1QkU6IQteFtDsSrXTuOnZiOoOnqP71VH/lxr4F2ONEjuj09Mt9eGeRrqq7J4kskwMbS7dcQFOtVBsniC0D7yo9xtIthP8ADvwI+OIa8kJZCU5VgDtJxG/oxweQ/ZtLfmTN88u2c6+H/gR8cA2mWz/t/wCB/riFesbzhK0E9xhKcSkZKgAOZMTpx9Sr2VT9SbDtMtnOSJ/8D/XFJ2l2z2T/AOB/riEhMMk/prf3wi5SnIz3RVWvIj9l0r1Jk+eXbX1M/wDgR8cHzzLa7J/8D/XEMtLadBLLrbgHHcUFY9EDu62grWQlI4knAEOkh9l05xyTN88y2uyf/A/1wDaZbP1M/wDgR8cQmh5txO82pKk8ik5HpgLqEnBUkHvIjHpr1L9lU/Um355tsY4T/wCB/rh/POtkcp/8D/XEKJUCMpII7RDUttJwpaQe8gQ6S9SfZVP1/cmo7TbZ47tQ/Aj44StqNtp4IqB/8EfHELJUlWQFJPPQ5h5xF6S9S/ZdP1JOr21kraU1Q6apKyP1RN4O75EAkHznzRjNiFpy+0ra/TaJcE5MOS0yXJqdO9lcwltO8WyrkFaAnkMgY0I0XjwiX+hx+39SvuKb+DEY2R2QbR36PT11TSgjvSWZal5dthhpDTTaQhtCEgJSkDAAA4ARXDEBjxT6I+dn/wDc5OH/AOapz4VyM50ozmq259zzP5TUYNw//E5O6f40zfwrkZjpPnNVt37nmfymo13/AM1o/Kzbpl/g9/5kRQy+RovJ749RMIHbFmDrDJxqSBH0ykz5jYi88LbH1Xohicb7FQkUisLAUKPVCDqCJJ3BH3sVIpNUL3UJpdRU9u7/AFYlHCvdzjexu5xnTPDMN/1L036Fbc+0DwXFyiqtDQhZ80YYofL4l22Hlvle4GkNkuFWcbu6BnOdMYzHoJKqGZVKik1IzCEha2RJuFxKTwUU7uQD2kQduB0d3kZj1YZHJz0D44zWz68pChXpTKtPJmDKyzqlObiQVYKFDQZ14iNTFKrG4pTlDq7aUjKlLkHkhI7SSnAjylpSYmppErJyr81MOZKGWGlOOKxxwlIJPmEOo3yma56aMlsku5td7XZKVm76lVZRL6ZeZdCmwtIBxupGoz3RiDV2if3Qxjp+nztOeDNSkJyQdKSoNzcutlZSOJCVgHHfFE5KTckpAnJKalN8ZR4QwtvfHaN4DI1Go7YKb9QtPGC2pdjJmrtY4LHmjxcqTS9Tvk+SLDwScUy28mSnC06d1pwS6yhZ10SrGFHQ6DsMegplW5UiqHySbvyYdX6mao9Eeypts8leiPMzLf2XoilMlUfCPBvU2f8ACCjfDPgrnWFOcb27jOM6Z4R7ij1lQz6iVYDnmQd+TDqfUvSfoePhTff6IpXMb2iAQTzjyKNMg5B7IoxiDkwkiVujGMXxVSedKPwzcYTa0f7808f9vlfeajM9GZRF8VMEf4LPwzcYTa3+3JPcP1dK/ktR8zD+b2flR9NYv8Gr/Mz6PwiM8YqhZjajTg+efSatCkWHtlnqZbqVSkk/LM1FplvxEyynFLBQ3jgkFvI7N7A0Aii2tqU0w0mXrkmqb3R+qWSEuH7ZJwD5QR5I2LpuH+/0v+RJT8t+IVBAEevRFTqW48DXaau2bUkTT8822sZUmfB/iR8cL559sfU1D8D/AFxC6ld5ikEKzgg4468I2OqPqed9l0/Umr559sfUz/4H+uD559s/Uz/4H+uIVVhKcqIAHMnEUqWlON9SU54ZOInSQ+yqH6k2jafbP1M/+B/rg+edbPZP/gf64hNDjazhK0EngARFe6N4p0yOIzr6IdJE+y6fr+5NXzz7X+pn/wAB/XD+efbGOE/+B/riE1bqRngBxinrEaYIMOlH1H2VT9SbTtPtjsqH4H+uEdqFsD2M/wDgf64hFEwwtfVpdQVjikKGfRHooBIySAO0nAh0o+pfsqld0yahtRtj6mf/AAI+OAbT7Z+pqH4EfHEJJKFnCVpUe4gwusQFbmRvdnOHSj6j7Kp+pN/zzbYPKf8AwP8AXHk7tPttCd5tuorI4BLQGfSqIZ3kpGVEJHaTiK8A8hDopkXsylev7m6XZtOq1WlXJGnMKpsovRa+sy84OzI0SO0DPliWug3Z1MrlxVO9Kj9NdojglpGXKBuodWgKLxP1QSd0DllR1yMc3KQOWsdb/wBj/GLYu0f70a+ARGq+OytpHraGmuuWILB1AoxQNDmGo6Qo8w9jucd9O6j0qnXdQa9KS/VT9Ul3W5spPiu9UUbiiPqsLxnmAM8BENWrf1VozKZN9rw+STolC14W2OxKtdO4+5E79P5pJqNm6/uU4fdZjl5O6CRkZHLOoj2dHZKNaaZ4+rrhOxqSJel9pNAUkLdl59CuYLaVe6FR6naVbQ/c578APjiHAtJXuZSVccc4rKRpnAJ4R3eKmee9HWTD88q2h+5z34AfHB88u2x+5T34AfHENlbQJytGn2QhLcSBnKcQ8XMeCrJkO0u2/wDJT34AfHAdpttf5Ke/Aj44hczDWAS4jB0ByMQB5o8HW/vhE8XMvgK/Qmj55ttf5Gf/AAA+OGNplsn9yn/wCfjiGFONg4UtIPeoCKkrbPrVpOBnQiL4qY8DWTKNpdsn9ynvwA+OKhtLtn/Jz/4AfHEL9czydb++EVZ/7xDxcx4Ksmb55ds/5Oe/AD44R2l20ODU/wDgR8cQx1qArdyMnlzj0Tg8BE8VNh6KtEwK2mW3n9JnvwA+OPJzaZbwG83Lz6lcgGkg/lREXWMh3qi60HPqN8b3oipaUpICilJPAE4zF8VYPBV+aNrvDaBUqtLrkae0qnya9FkLy66OwketHaBx7YmDoJW7S6hcNauadbU7P0xCJeTCvWtdYDvrH2eBug8hntjm94hpOXFBI7VHEdTdAUgsXaRj9NluH2q44NZZKUG2zv0lcYSSijqiFmEIZ4R5J6YjABB2weaIAggHmg07IEDjBnvg80KKUcGdYIUUBmHBxgMQoZhHhDhHhwikKuUKHyimIUIIIcAKHBwggAg7oUEAEHmg5wQAQQQQAQ4MQsQBzt08P2AW3/LR/wDTuxyBHX3Ty/a/tr+Wj/6d2OQCY9PS/LPP1XxgTBmCDSOk5y4pZQqrU9DiUqQqcYSpJGQQXUggjmI6x2+VoWLfDVGtvYLbtxSLki3MqmxQSsJcUtxJRltpQyAlJ118aOTaakeq0gonAE4wSTwGHUx1B0n9sN6W1tPYp1kXWy1SVUdl5aWWWH0deXn0q8YpJzupRpns01149RGUpxSO2iUI1tyLLo1Gm33tTveoVvZ1Qaa7LUuUS3STTk9XLrBcBwhxAKVKwM6DOkY+5ru2gSdr1GYq3RotyjSIlVh+eMklIlklOCvRORjOYveiDca6hf1/1u463LMVKqSMspU0+tDPWO7zoyBoNBu8B2RbXHs22jO23PS1Y6RMjVZASy/CJR2fcWJhATkoILmucY1jRt22bZf8nQmnDKM70Zb2t/aDeHzH1TZbZ0oiUo6plM41KIccdU2tlvxgpscesyTk6iNHkaxKbdb+oVhNWXQLTlmag9NTc5SQEvOsNIWlSPWJ45GuTg4ONIsuhBU5KS2zzE1PzTMmyq3phO++4EDeL8sQnJ56HTuMaJshvU7P9rEldLkup+Vl5p9qaQjVSmHCpKintI0VjnjHOM+nictvl2NfUzGOSab32z2js8uifsiytlVtzlHprxl511/dQqadSMOcG1ZIPilS94kg6aa2nR6csi9Ok7U36NZkrTbdeoDy2aXNtNuoS6l6Xy4G8FDec4CU5A118YgX147E7Z2kXPPXvYu0u32KPVXTMzLbyN9Uu6rVzGFp4nUpUAQScmPDo5061LR6UNSkaHdstWqGzQH0tVJxaEJU4p2Xy3vDCVkY9cnQ5xxSYxah03tzkyjuc1uxg1LZ1sc2hS+2SkzlbsKfFDRWFuTCphppbHUlS8ZTvHKdU6YjAdJeTkqVtyuGQpslLSUo2WerYl2kttoy0jglIAEbHsz2n39M7b6PKVa/Ku5SHKy42+0/NgMFoFzAPAbuiYwnSjdlZzbrcM1KTDUwyvqSlxpYWk/SkcxpG6verFu9DTc4OHu+pGm9k8IMwsY5QCOzJxMcdC9A79s+uj/cv/vIjnqOhOgcf76Nc/kU/Dtxp1Hy2bdP8xHZ3OGOGIXogEeOeuc99PP9qqj4/wA+NfAuxxl78dm9PP8AappH8ttfAuxxhnSPU0fyzzNX8wqzjlEsdEmSp9W25yUjVJCVnpQ02bUpiZZS42SAjBKVAjI1iJIlfohTkpT9u8jNT80zKMCmzaS684EJBIRgZOmY2Xt9N4MNOl1Fk2us7Ydnzd+VS3Ls2LWiaFI1R+RenpeUbL7SG3FN9dudVrwyQlQOM4ydDnaFskolodLumUFNPYqNt1KjzM9Ky88hMwhCgN1SMLzndIBBPJYHKMbXdhtnrvaq3Rd21q22Lcnam/PTEs2tKHVIddUvqesLmATvbuQM9muI2K2dptIvnpdUqtScymVt+nUaZkpN2Z+lBw43lOEKwU7xIAB1wgHnHA849z05O9NZ9714FcdZv6lXFVJSm9GC3Jymyk263LTngLaQ8yhZCXNE6ZSArzxqGxWhWTQdjtX22XrRJevNmbWxSaW8lKmCrrQgeKoEbxcJAUoHdSnIHHO9XTs+2hVe46tOSfSKYlKfOTjzsvJpn3QGGlrJS34roGEpIGnZGjbJarZ9X2Y3DsHvKvS1G6upuqo1TUQGFLS9kbpJxnrElQSSN5K8AnWMo52cfr3EsbuV+BaXPtytG7rUqkneGyijpqDcsr1Km5B1IUys9qyhK2wOOUkg4wRGxtydn7CdlNuXBWrTpt13xXU9c14alPVywKQo7pUlW4lKSlPijKirkDppd6bCKLaNoVap3TtVoqJsNYpstKt73hKuaSneK1EjIG7606nIGI2+Vm7a6QWy63bfnblkLZvmgJDaW5sAomUBO4opyRvJUAlXiklJGDnjGctmMRzt8zXHd3ljce1Ml7L6Qdh3I9L2jTbUviitCZD9PQN19JSooKlBKStKtxSSlWSnAIPCLayKhb9m9EG3L7esG2bhqkzUHZZaqjJtqUpK5p8AlzcKjgJSB3RkaSzanR2sa42nbqkLkviusBhmUktA0gBQQVDeUUoBUtRWrGeABIAj1sa1ZC+Oh9bVltXXR6NOy885MKVOOA4CJl44KAoHUKBjB9v8uTNYzh/Fgx9rU/Z7t8s24JSnWNSrKvKkMiZZdpTaUtvAg7pVupRvpJBSpKhkaEHgRe7FmFS3RSo9y0PZjRrzuB2fmGzLzEm2txbZmXckrKSTugAa8oooTlj9Hm0bgfReFPuq96vLiXZl5DAS0kb25kBStxIJKipRGcAAHAEPY5KTNX6JlItihbQpaz6y3Un3PCzOFl1LaZlwlJCVJVhQxpwIjGaf9PwmUWl8XcjrbncdxzdJp1NuPY9R7CUqYL7D8qylDkxupKSjRIykb4PHiBESnB1ESxtwsS56PbcpWri2uSt7BqaTLsy/hS3nGesBJWN5asDxBnzREiDpHfQ1swjg1HM8lYiYOhx+39SvuKb+DiHx5Il/ocft/wBJ+4pv4OLf8tmFPzEd8wjDHCFHiHuHzsc06Tk7jh81M38K5GW6Tn6627r+95n8pqMO5/8A1Nz3b81U58K5GX6Tf6627x/U0z+U1Gu/+a0flZ0aX+TX/mREYjxqGfAJj+KV7xj2BxFvPhbko8hAJUptQA7Tgx9G+x81D4kd9X/MbX2rbtQbKpWgPINPT6oeqWMg7jfV7mSPs8+aObL82kbVrO2206uXgil/NFR5NDa5OSO7LzEo4SstqIJ1V28ilJwcayXtMqWyjaLRLXbc23fMy9SZHqnW5JS/pilIbB39RqkoI85iMRYWykbRqK3UNr7detxTS36tOTRKHCW1IDcsFZJO/vKyeSUKxgkR5tS25yv9D0p8pYZOdXouz23KhN9JhluZmpGZpTcxI0wSpAE274vXajxVKBQnUAJytRJ3tNM6GVXrV07VL8r9ZmkzVUnacw6tWMISouL3UoB9ahOAAOwduTFy10gqLUdrNSt6uNSPzrpyUNLabcYHVthIP08jGja8lG7jQBs6YVGF6P8AXdm+zTapejCtoFMft2cp7KKZUFOElQK3D1atP0xGcHtGDziOLUWpLnyImpNbXwZ++Kh0pKVZFZn7klbObo7Ei6ueUwkKcDO6d/dG967GYtKRV5bYR0crbuahUmSnLruwtlc9NI3gylTanAnQ5KEJASEAgEkqOpOdNm7L2UuU59v6JioT6upUBLu75Q6caJKSo6E6Yi9sG77DvvYtT9l+1GpuW3N0hSF0mrpTlDaUjCQpRBSkpSotkK0UnBBB4ZKL2rjK8+CyaUvr5Gr7Utudw3/synrZuig0Kami4H2Koy2ptyXCRkpQg72FHVJUFDxVKGDmN66bzQc+duQONImST+LRo20y0djlu2E5KW9fszdt1uzCd1+TwJVDJ0WlYGUAbpJGFFe9j2OREg1u5dlu2mwbblLnvZmx7ooTJYUqabBacSUpSvdKiEqSrcQoYUCMYI5Rse2MozisI1rc04yeWOs1OdtnobbO69TOoE9I1tp5kvI30bwVM+uGRkeeNt2YbZLvuDYLf96VNukGrW/1ngfUyhQ0d1hLg3klRJ1V2iIp6QN9WYvZtbOynZ/UnKxTaK4l6ZqJHiuqQhQABwAolS1KJToOEWmyS6bbpHRz2l2xVKxLytYq3W+p8qvO/MZlkJG7gY1UCNTGqUHKGcc5MlNKe3Pkbr0Yb+r+0bpHO1m5vADMy9qPyyPBJctI3BNMK1BUrJys6+SNmuac6U9OlqrOuS1n+pLCHnCrAK+oGTwz67d92Ig6IlxW7ZW1iarVz1WXpkguiPyyX3s7pdU/LqCdAdSlCj5oz9RtPZBNzk06rpKVJCJh1ayyd8oAUSd3BOCNcRZQ22Yxx+ArlvhlPkgSW3US7TaM7iUgJz2Y0is6mPFpSlNpKkbiiNU5ziKwe2PSPMxySn0aP2cVLH+a1fDNxhNrhztjnvu6V95qMz0az+jepHX9a1fDNxhNrePnwVA/7bK/ktR85D+bWflPp7P5LX+Zn0jgg5wCMkaDhLpu/t9L/kSU+EfiFNTpE19N39vpf8iSn5b8QrnTMezpflI8bU/MZ5vDdZWc4O6Y672v7J6VcWwaiVW1qTTpW5KbTmZ3clZdDbk6z1aetQrdAKjjCgT7JIHOOQ5rKmFgD2J96Osdod9t2TP7ILnpsyzOtSlMck6mww8lSlS7iGCtJAPrgUBQB4lAGmcxhqN2Y7TPT7dr3GG6F+zilVZh6+brp8pNy02pclRZWdaStD2NXXghWcnQpGmQErPAxedGCjUybmNqrzlsUutTFPqT/gEtMyaHAClx7dbSCPFGgGBiMhZe0qg3F0krfkqA6xSLHodHmWZBpafBmi6UpBXuHATod1IxkAK+qiw6NFSkJaf2tSarhkaRMz1UmUycw7NJbwVOPBLiTkEgZByI5p73ncdUNiS29jA7R7lvduxKsmv9H237XkZiXMs5VG5RKVyxcIQlSVAaK3lADvIjdJvZXT736KFqOUWQkmLqYpDFQlnGmkodnFJbHWNrIwVbwVjJzhW6fLHu0LZ5fCLJqT1a2/ylxyUpLmZXTnam86Jkt+MlO6p0gnIBGQcEA8o2GvbQH7N2NbEq1QpxiZnaahsTkmh8bzjRliHGlgHTPAZ0Cgk40i5eEody5jy5djDdDDZ5TLoq0xetyyspNUWWUZGny040lbc1NKSFKVuqGFbicgDXUq4bsX2z7Zja9d2z7R6/c0mx8ytrzr2JBDYS04v12ClOBuISD4vAlQ7NdkY2p2xcu3qyqbbKmKVaFNdmZ51bjfgqXp15t0rWpKsYxvq1PrlOKPIE4WxNodsW7tn2j0C6JtpNr3NOOhU6le820563JIz4ikqI3uCSgZ0JIr6snJteRgulFJJmNtzbjY9wXHIWrXtj9rydpTswiWa3Wmy5K753W1qQGwkalIO6Ru5yCca7Fsx2a0S0el1ULPelWqpRlW49UJFqfaS/uIW80kJO9nKklLiQo64OuTknC0fYJZ1r12Ruu5Nq9vTNpyL6Jps+KlcyEKCm0qVvlJyQM7oO9wAGYyey3aXSb06XlQutcwinUlNuu0+Scm1horbQ80Qo72MKUpSzu8cY78YT7PZ2Mo8Y39y52e31ae0vanN7OK1sktFcmHptpMzJsJLzHUqUkOKG5lAOMbwUCCoY4xidmlrWXNXXfmwSvy0lMPomHl29W1yzZm2wQlZbDu7vb6CoK4+NhegAxG07I9uxue7Lls6sLpFtTSvCk0iryraEoJQtSfH38pUrGFjkoBXYM8yUd2tW/tMp6p2fV6syFcZMxOpmS5vudenrHOsJypKwVEqJ1So54kRnXByyu3BJzSx+JL9HtlnYjsjqtz3vRKbOXpVpldNo8lNMJfbY3SR1oCgRg7pdJ0ykNjiY58YUpKEpKlKwMZUck9574nbpt1VmsbYJJMnUm56QlqGz1QafDjTbinn+sxg4CiEt55kJT2CIMCNY6tPFuO592cuoa3bV5Fe9qI656AH7F7t/lRr4BEciYxwjrv8Asf5/Qvd38qNfAIhq/ll0nxnTa4p1ENfGFHknpnJP9kBdIqtmDPFmd99mNU9R6PdvQ7FwU6jU9m4bTn9yoPy0shDz7KDgqcUBlf0lxKySTkoPONr/ALIA3/diyzn9wnffYjWeh5cNFRVbosG53WE0W4KcpakzDgQ2paPEWkk81NrGP4sx3LKpUo+Rw5i7nF+ZIsjsmoh6L/zNrp9PVerlGVWUuqZR4Ulwr60DrMb24Dhvj63SIpalaXavQ2qF0zdKkXa9dVQVL0x6alkqeYY9YS2ojeT9LadWCCNVgxuc1tOlGumuioCbZFFblU24XOsHUhkp6zeB4Y64pH/8o1Hpk1KjNC2NntpvtvUSgUkuIDLwdRvqBbbTvZJKkoQrOf8AKCMYKbai/Pk2vYve9CQ9tV723sxteyC1s2s2rqrFN6x5U9LNtkFCGuH0s5zvnOf6Y1nazZ1oOPbIr+t625e32blrVPYnKOhlKGSlxaV6tgBOcApOAAoHUcI3vadtZlrEt+wfAKTQ7ll3pJAnkLWlx5gIQ1kNnJCVEFXHTIEar0h51dZ2sbM7vp9xMVKz5ipU/wAEbbcSESLomEKWVpBz4yBneUPF3FDTnhGMs/uZZiY/bVc1H2WbeK81IbPLWq8nMUmRKZWalkIaYKetJUhIQQCrOug4CN1243lb+z63LRqsjsrsyoOV2WLzyHpJtAaIQhWEkIOfXHj2RD/THnZOf231GZkJpmaYVSZVIcZWFpJAcyMjnrGy9LWp06fsXZsiSnZWaWzIKDqWXUrKD1TehwdI2qpNQ+vc1ysw5peRtOyOWda6LtOuWhbMaHeNwu1SaQZZ+TbUpTZm3QTvEZwkYA7sCI52q1q4p2q2hSrm2O0Www5XJZ5tyWYQlU2kOJQptWE4KcLBIPdpEgbJEz1Y6J9JoFvX/J2hWvVOZe8KVOdU4lsTTpKcAhWFaeURHO1G0rqo1RtOsXTtakr0SiuyzDTQmi4qWBcStS8lRwnxBnzRrhxJtmbawkTlthFft+82qXZvR7tu66SuWbccmzItI+mKUoKbzu4GAEnJ7YgXpe0Oz7V2ltytpS0pIg01MxUqdJpCWpR3eO6AE6JK06lIxwBx42s7baLbu2677TWbM24SltU1Mo214G3VlpQHUqWVOFCFhJzvDiNcaxY3WLDvvb9ZLXq1R6m7bcguar1TQttLL621I6llSh4qldaVL3QTujOnjGMapODTLZFTWGO1tnFgSNoU/Y3WqdTDe9Xt+YqLs8uWaMy04VDUOEb6d1Rwn7Fk9kQl0ZdnTF67TZ2m3bLrZkLfZW9VZUr3Sp5LnVhlRHsd5LhVg67mOBiRrj6Qezo7Q3Lsb2Xv1KqSLimZWrifCXXGUbyQpCcaJKSSEnjva8YydwXLbOzjpHi9mKhKTNnXtSktVByWWHfB5lJBDi0JyQkp3eH1ayR4sZxdkU013MGq5PKfY1n6Iux/DlUNjY/QXLHyW0tJaaDrjfJwMlAbGeO6TnvzGR2ASVAuWx9q05TrUl0NlSl0uScbE27LBTKt1CFFJVnOuBwJwM4zGCd6ONseHmsy21iiMWST1yZjfQXUMcd0OFe4cDQLI7yDGX6LVcp1k21tMep1fkar4E5v059Y8HTO7jRKVBCjvYJivaoe73KsuXvYwWNco9F2D7O2WKtTqZW9pVwsbzaZqXS+xSmBjKkhQIJCsa8Vr+xTpsfQIQrwe7lKUpai9LkqUrJUcLySeZjDUe46Z0gdlK6BdtUptO2h0LL9Pn3t1lM42cZ7AArRC0jgoIXjgIz/AEDkOst3nLzDSmnmphht1tRBKFJCwRppoQRpFlLNct3cw/rW3sdPQjFUUqMchvAwoIIECCDlB3QKEEEEUBBBBABD7IXOCIBwj5YIDwigqPDWFD4jjCiECEMZhwoFCCAQQAQaQcoIAPLBD5wQAQcoPPBmIQIB7sEEUHOvTz/YBbf8tH/07scfx2B08Ek7PrcUBoK1r+LuxyBiPT0vyzg1Pxhw5wCCCOk5x5ilAS2nCEpSnOcJGBDghkglpSsDrEhYH1QziMtJ2lUZu2pu5WaayKXJr3Hpla20AK00SCQVHUcM6nEYknAzxiVNqC/UfYbadHljuNzA8JeCdAtfVqWSf5y8+iMo89zXOTTjFeZH9UtOsSqpNuo0WaaM8oCUS8z+nE4xug8T4w9MZBWz29kDHzJ1XH8REqbX5sCqbMxr+qWANfsmIzd/UbahVbkU/alxMSNNLCEpZXM7h3xneONxXHTnGzprGTnWok8LPfPc5+VZNxuJn5ldtvKTTf1YVhsLZ8UK1STvHxSDoDGLO48gJWlC09ihkRLuyF2uI2xVek3DOKnn5qWdYn1Fe8HFtFIBBwMgJ3hwHGInmpI06emacVFfgj62Co8VbiinPuRqcWlk642NycX5YKFAKG6QCkjBBGkCQlKcJSEgcABgCGBBEMmw8kEPMHniGIR0J0Dv20a5/Ip+GbjnuOhOgeD88+unGnqL/wC8iNOo+Wzfp/mI7NMAhGGI8g9c576eefnU0j+W2vgnY4wEdpdO9JVskpZ7K4yP/Kdji7EeppPlnmav5gDHMQnEIWndWgLT2EZEVYg5R1HKeLcqw2rebZbQe1KQDFagFJ3FpCh2EZEVmEfLBlbb7niGpdOT1DX3gjY5y0LglqBTKzNSCUSVUcS1JjrUFx4q9aA3ne1xppzHbGuLZXMqTLJVul9aWgocio4z7sTVt2qRY2v2jQWvpcpTxJraQDgBS5nd4dyW0+kxz23OElFGE92UkRgmy62xW00VNvzTVUcR1iZQMbrqk6nOOzQ+iLyd2e3kxLqXNWhVepGqt6UKh6BmJuq0wg9KenDe19SUn/hejRry2qXpbl/1kytYdmJGSnXQmSeCS0ptJ9ZnGRpzB0jVG+yfwJdsmlXWSawR7aNu1S4qmaRb8ow5NBtT3VF1DQ3UkAnxiM4JGg11jFTLATMONTUqlLzayhxDiPGSoHBBB4EEEeaJu2otsW3t2s+4KajwdVYcQmZaSN0FSnEtKUccyl0Z70Rou3aRRIbU6qlrRMwG5kjkCtAz7oJ88Z16lzkl6myE3Jp+qyaUkAJ3UpSlPYBgRQqWYWoqWy2pXaUgmPRPlioR0m3LR4olmG1bzbSEKxjKU4MegSBFUIxQ233DSJf6HP7f1J+45v4OIf4RMHQ4wdv9J+45v4ONV/y2bafmI74gMOEY8M9s+dLisdJuez9dU58K5GX6TP66279zzP5TUYrakPmR6StamJlJQzK14TalKGB1Tu6tSvIAtXojbekjR3XaLS60gFbck+th1Q1CUu43VeQqSkecRr1L2+0qJvs00dOjTl7K1Fa7pp/oQZjJEGBFWMcYUfSHyxUFY4Zh9YeRPpiiEOMUAsFXGMzYVpVK8rkRRKattp3qVvuOu53G0JwMnHaVJAHf3RiQcGJg2DbkhZV+VxrSaakw2lQ4gJbWoY86vcEcPtG+VFDnHvwju9n0RvvUJdv/AOGj2rYFwXMqoG2VSNSlpGaMsuYEyG0OqAzvI3hkpI1B5xdXNszvS3KFN1urU+WbkZRIW6pubStQBIGg56kRuOwZqRa2WXkzOT7tNk+sKXppnO+wjwdIK045gaxpN5StqStDUuh7SK7cE0XUJMlNqc6tSM+Mo5AGmAR3x5sPaGolqXTnhNLt/wAnpT9n6eOmjdjlpvuixvC0q7a9Nk6lVW5YyM6MsTMvMB1s+LvDJ0xlOSPIY8qjZVZpdOpdVrzkjSZGpOobaW+99MRva7y2wMgAanXQccRKWwHrbns2oW9cdObqFvSkw2ZRc0d5PWb28WQDxSk7p7BvlPDSNJ27PVao7RKhLVxnqUSyOqk2QvKfB1ZIcHaVnJJxxG7ruwq1992pem4zHOX/ALY/5JboKKdMtTziWML09f8A/DAXtalSs64lUapKacWWUvNvNA7jiFEjIz2FJBHd3xiMeWJe24qTUdndhV95I8Melg2tXPCmkqOfOkREO9pHpezr5XUKUu/K/Y832hRGi9xj24f7gVHEUwQR3HEGRjSHy1hAemKhiAJO6NuRe1S0/wAFq+GbjB7WddsM+P8AbpUe41G69GmivqXVa6pBDTiUyTJx64hW+5jt9gPKDGm1VBu3b21K0/LyJ24JeXQUDilC0JWodoAQtXkEfNUyU/atsl2UcH1N0XD2PTGXdyb/AEPpHBCBhxsOU4R6bn7fS/5ElPhH4hXGkTb03UH5/CiedDlD/wCY/EKcMZj2tL8pHj6n5rEBjWBG43ncQhBPEgAZ8sImFxjf2OcHFBSClQCh2EZjIT1pVlu25G4JqnNinTzoalFKWgrcUc43UZ3sHBwccNeBGcY62tbS0NnC1AhJPInQRNu30pkr0tW2WB1cnT2GHEIToMqd6sHHcGv+Ixz3WNSUUYSt2NJEM1a256hzolKrR3adNbgcDbzO4rdJIBHdkH0GPah2/VKm5Mro9KmJxbCN+YUw1vbiddVHzH0GOkdvFCl7opM4ZBIdrlBSJgsJGXHZdzJKQBqfWkjvQRziuxKNJWdaE5b63EKrrkgqoVFKeKN9KkoT3AbpA7SlR5xz+MjsTS5OfxspQ3Y5OeqLbdx12RM5SKHPVGV3igustFSN4AHGfOPTFdXta5aLTlT9Voc/ISbZCVPPNbqEknA18sSVsUNQf2BzrVPr7VBmTPHq591QSln9JzknTUZT541Da8m6JC0y3U9pEvcsrMubipVh5Kt0pSVBZAJ0BHpxGS1c3No3QbnY4ejwaxWbeqVFdaVVKO7IOzCOsaLzO4pxOmSDzGo9Ii3pNv1O4JtUnSqU/UX0o31NMtb5CcgZPnIHnjovafSmLutlm35d5Ir0pIt1GRQeLiQNxaRzIPA9hUg90emwCiylsUuSlqgnqrgrjRn1sqThbUu2pCUoVzGOsBI7VHsjF61bM45NUdU9m7z/APv9DnZm1a1N2zNXAzTEv0qUcLUw4HEEtqGM7zed4AZGuOBzwyYxbTaUJ3UpASNAANImno6JbqM3dduPjflZ+SU4UHUA7xQT5wseiIbbG9Ltr5qQCfRHTVJuTT8jfC5zbQNYQndSkJHYBiKwRmKMc4aeMdGTYNQ0jrn+x/jFr3d/KjXwCY5H5R150A0/oTu1X+9Wh/5CI5dX8tnTpPjOllQhFSuEU+ePKPTOSv7ICr+69ljP7hO++xHLi2UOpKXEpUnmFDIjqHp/pUqsWWrB3eonhnlneYjmNAwMx62mX8NHlajixsoQyhKAgJSE4xu40itKEoACUpSOxIxDzDPojpwjS2wRuIzupSnPHAxmPFSGQ4pzqkBSxhRCRkjvj1jwn1FEo6tPrkoJHoiNiPfBnGLUr3qHJ1Zml/2nPPBmUCVoDjyiTjcbzvHODrjgM8NYx9SpM5SZxyUqMi7ITKQFLbdRuqwRkEjviSOkPMzFIqVs0emuGXFMkUzDO5oEuBW6hXm6s+mNwuSgS953vZFyMNhcnPtJM0BwKWx1yQR2HKknuxGagm2vQ5eu1FSfZ5IKrtq1CkTDaK1R3pN51O+gTLO6VgaZGeMeiLPrjPgKkW/No9UTuyhDGPCPF3sJ7dNfJE67WJRvaFbdOnaNlbrFcXS3HAMlCVLLal+TIQryERTeNTQ70gbWoEoQJOjthpKQeDi21kjHckIHpjJ1RJHVTcefqQ0dn12tJKlWfUEga/qX4o87etusXHOzFNpdORMzco2XXJZxxttxKQcHCVkEkEgEDhkdoie6pIXQNovhTO0OTlqZ4Sg+pKlJK9wAZbwdcnXyZjSZyovyPShl3G5N2TMwEy694AF5KmlfTNOIJSPvYOKiIXys/bJEaXgoBSScEZ1GIQQnJIQkE8cCM9tOkmqdtHr0rLpCWvCy4lI4DfAWfdUYwSeEas84OpYaTR4GTly71nUNb+c724M+mGuWbWoKU2lRTwJTkiLiDnE2oy3y9Twcl23EhLjaVgHgpORHVvQFATKXaAMDrZYDH2qo5YMdU9AgHwO7VY066XH/AAqjn1K/hs20N70dQwjD5wjHlnoCgghwKKCHBwi5IKHBnvg5wAQtIfdCgVBBBAOPCBQgMAgMUxKuULMM8IpEQo4UEEAEOFD88AKCCCAHkZg78QoOIgMDhQeaCAwEHGAwQBF3SltGau/Y/UWKe0XqhTnEVGWbSMqc6vO+gd5bUsDvxHA6VpWkLQQpJGQRzHbH1KPuxylt56Ns87VJm49mzDCm3z1j9E8VrdVrvKYUSEgHT6Wca5IPKOvTXKHDOW+rdyjmI+SDjyjM1Cz7wp0yqWn7RuFh5PrkmmPHHnSkj3Y8fUC4edt10f8A4x/5Ed6kmu5ydOXoYw+SGOWkZE0G4PrbrvtY/wDIg9Qrh+tqve1b/wAiLlE6c/Qx5GmuIkvaCldwbAbdqkqd9VLc8Emu1B3S3k+U7h8ihGiGgXGeFs172rf+RFw3IXqxJPyEvSLqak5j9Ol0SMylt37ZO7g8Bx7IqnFZRjKixuLS7G3X7fFArk/ZT0k5MqTR3mlzm+wU4CVNE7v1XrFcIxO1W6ZW4bzXU6LNzYkzLNNje3mzvJznTPeI1r5nriH+LNe9q3/kQfM/cf1tV72rf+RDq+WRHS7cYTJH6PLRbueo3LNqKZGmSLnXOrOm8og8Tz3UqPnHbEXzMw5OzL048AlyYcU8sdilEqPumMnL0682JJ6RYpV0tSj5y8w3IzSW3DoPGSE4PAcY8RQLj+tqv+1b/wAiK7E0kSOnnGTlgx2dIfmjI+oFxfW1Xvat/wCRFJoNw/W1Xvat/wCRGOUbOnP0LDTugMX/AKg3Dn9jVe9q3/kR6MW1dMw6lti1LgcWo4ATS3+P3kRyS8x0p+hjAocDHW3QOtd1mjV+9H21Jbn3ESMmpQ0WhokuLT3b6inytxHOybo1Xfcs81OXlLvW1Rkrytpak+GTA7EpBPVg8N5XjccJ4GO1KFS5CiUiVpNLlGpORlGktMMNDCG0AYAAjh1N6ktkTs01Di90i+74OfGCCOE7SM+k5Z05eux2q0ynMqeqEqpuelG0jKnFtK3igajVSN9I+2j59JWhaA4lQUlQyCOYj6o500jlfpD9HGeqdXmrr2dtMdfMqLs5RyQ2lxw5KnGVHCQonik4BJzka569Lds4Zy6mlzw0cq7w7oM9gEZipWbeVMmVS1StC4ZZ5PrkmmvKA86UkHzGLX1BuEf4tV32rf8AkR6Kmnzk4OlP0LH3IOcX4oVw/W1Xfat/5EVeoVw50tuu+1b/AMiLuXqOlP0Ma6lYbK2SOtT4zf2w1HuxMHSElmVXlaG0JlZdpM63LFTiBkDqnet07SULOn2BiMxQbi+tmv8AtXMfIi4mZG9ZintU56lXW5Isq3mpZclNFps66pQU4B1PAczGi2tTkpZ7GPSs3J4N1qW0C35jbnJ3k07N+pTVPTLrJYIXvgOD1vHHjCLqauPYwquzFwPU6s1GdceMwplxCi2tZOfWqITjPI6RGZty4/rYr/tU/wDIhfM7cfH5mK/7Vv8AyI1eHh5Mj0uccPtg3+hVWobVNt9GqEzKdSiXcQ6iXQ4VhhlklzJJAySsjJwMlQ7BGE21VGXq+0yrzUstLrLS0yyFpOQrq0hJI/nb3ojD0uQvWlPqmKZSbrkHloKFOS0jNNKUkkEpJSkHGQNO6LdNBuIJCRbFeAAwAKW/gD7yNkK4Rnuz5EWnmpZSMbjEHuRkvUG4vrar3tW/8iKfUG4vrar3tY/8iOjcvU2dKfoWGYIv/UG4vrar3tW/8iGm37lWQlFsXAonkKVMH/kibl6jpT9DH+WOiegnaszPbQKpeDiD4DS5NUk2vGi5h0oUQPtW06/xg7I1PZh0edoN4TqFVSnvWvSdCubnmx1qh2Ns53icc1bo8vCO3bBtKiWTa0nbtvygl5GVTpnVbijqpaz7JROpMcWqvi47YnZpaJKW5megxBiCPNPROTenLs6dMxL7SqdLrdZDKZKrpQjIQkFXVvnu8YoUdeKOABjRtle0Cl12iJtC6SwuY6sy7RmNW51rGAlWdN8DTGdcZHMDuOflJeelHZSbYbmJd5BbdadSFIWkjBBB0IxyjkXbJ0U59ibmKts1UzNSbnjGiTK9xbfEkMuqO6RwwheMa+NjAGV1VeqqVVjw12foZabUWaO7q1rKfdeqNHuLYs4ZpTtv1dKJdXCWnW1FSPI4PXDyjPeYxI2L3Sf39Svv1/JiyS3tktN0U9yQvCU3depdkHJlI8hKFjHkMXAu/a+n96XAf/wK/wA1GuNPtSCxG2LX1Oh2+x7HulTJP6dj3TsUujj6oUof+Iv5MHzlbmH+EKV+EX8mLdV47YP4LcHtCr81Hmbt2wE/pFwj/wDAq/NRdvtb78SZ9jf25mo3VQ5+2q69R6mhKZhtKXEqQcocQrgtJ4kZBHlBjeuj3UZd6qV60554NMVqQIbUojG+nKVDylK84+wMa1cjm0C5CwquUivTqpfPVKVQ1oUgHiMpaBwcDQ6aRh/mduPnbNe9q3/kR6NlMtRp+na1u+nqeTCyOn1PUpi3H6+htdg3czZFKrtrXHbzlUXMzRRNth9KEeKgNqScg7wOM55gwq7cOz2eoc5J0vZxL0qfeZUiXnQ8klhZ4LwBriNXFv3GP8Wa+T/Jb/yIZoFyfWxX/at/5ERez6N/Ub5ffkr12p2dNL3V24NovS+JOo2lTbUtqlP0OkyZS46nrwXHnAcg7ycey8cniVYPKFe97rvugUmmOURxV1MuJZZnW3U7kxvHdKSCAQFeKrjgKHHGY1c2/ch/xZr5H8lv/IhC37jGvzM1/wBq3/kRfAaeOHHhrz/EnjNTLKnynhYx6G/dICotS8xb9nSbiXGqNIhTyk+t31AJSB5EpJP24jRbXos9cdcYo9NbCph7KiVHCW0D1y1diRkekDnHl8z9xc7ZrvtW/wDIjL205fttvvPUOjV2UcfSEOq9RXFlSQSQPGbOBk8otVMtPp+nU05fX1Fli1Op6l0Wo/T0NnVsUuflUaSf/EX8mKfnK3R/D6V+EX8mLYXhtfz+p6+f/wAAr81D+bDa/jBlq/7QK/NR5u32t9+J6+fY39uZcHYvdA/f9J+/X8mMjQ9ic2uaQqt1lpLAPjMybZK192+rRI8xPZ2xhjd214jRi4R/+BV+Zi3cf2y3KvwBuTvGZLn7kxTXJYHuKkoR7pxEdXtSaxK2KQVnset7o0yb+vYkTaBfdGsugm2bZ8HTUEt9Sltg+LJJI1Uoj2euQOOTkxkehFs4cqdyq2hzsulFKpiVy1MCkfp0wQEqcSfqUJ3k55qUeG7rb7I+ivX6tMM1LaI6qi08L3lUyXcSuafGeC3EkpbB57pKsc0nh2LRqZIUaly1LpcmxJyMq2GmJdlAShtAGAABwjPT0V6Stwg8t936nPqtTZrbVZYsJdl6F5gQYgg9EDE5M6e1puImaJfjDS1NBv1LnVJTkI8ZS2VKPIZU4nPapIjlrf3hpwj6i3PQ6ZcdDnKLWZNqckJtotPsODIUk/098cSbU+jVe1pTq37Wlpi6KJ+5qa3fC2R2ON6b+PqkcfqRHoaXUJLazz9Tp23uiQriKgnEZFy3LmbUUOWtcCFDiDSpgf8AJDTQLhx+xuve1b/yI79yfmcTrn6GKmN8sOBo7qykhJ7DyiY9vky3PTtpX0wCuRm2G21uJ1wUr60Dy4U597EY+oFw/W1X/at/5Eej1OvVdMTSzSrrVT0r30yipGaLKVZzkI3d0HJJzjnGi2ClJNM1vTylJNrsSDcG1aUY2vNXjbqHZqT8BRKvy7wLPXJClkpOhxjKSDg6iPCzNociivXZWrmde8JrMulDQZaKwjG+EoHYkBSQIjpNu3IB+xiv+1b/AMiKxb1yfWxX/auY+RGKpqxgj0fGFFm67OrgsmU2WzNnXWZ4omZouuJl21apHVlOFJ4eMiMNfUnsuctebbtFurprCtwMmZUvq8bw385+xz58RhBb1x/WzX/auY+RFXzP3H9bNf8AaqY+RDoV5znuZxpsjLcs98m83tf8ou9bduS2XHlrpkkGHUPtlsOa+Mg9qSOfI4PKPaztpksNrs1etz9bLMOU5coyywku9SnrGlJQNASPFWScDJJ01iPzQLj+tmv+1Ux8iPNVvXIR+xmv+1b/AMiK6acYMVpnjG36Em7BJtFEoV2XjODq5diVMuysjGVarIHaclsY7TERNH6ShH1KQPcjLepl5mmClmk3X6nhfWCU8Bmep3853tzd3c554jxbt+4x/izXvat/5EWvCk233LDTSi28MssZEU6jlGVTb9x4/Y1Xvat/5EXEhaN2z8ymXkrSuF51ZwlIpb4z5ykD3Y3tr1MunP0MA4tKEnOAOZju3ocWtM2zsfZm5+XUxO1uaXUFoUMKS2QENAjt3EJVjlvYiKdh/Rkqk3UZavbSpZEnJNK30UUqS44+QfF69SSUpRz3ASTpkjVMddtoS2kISkBI0AA0Eedqb1P3YnfpqHD3pHoo9kLHfBz5QRyHYQD04LVmKrs2krjk2i4uhTfWzISnKhLuJ3Fq8iVbij3AnlHFm8NQO2PqZOsMzcs5KzLLbzDqShxtaQpK0kYIIPEEco422y9GWvUaffquzuXVVqStW96mb4EzLfYoKiA4jsGQocPGjt0t6itsji1NLk9yOfPNAIy85at1yT6mJu07hadQcKSaW/ofKEYjwFBuHnbde9rH/kR3qS9Ti6c/Qx58npjymWuul3GuBWgpz5RGV9Qbh+tuve1j/wAiGKDcX1tV72rf+RDKHTn6Eh7eZcVqj2xeknhcrNyglnFj2K9VgHz9YPNHvs42lUm3dniqVPuTSqpKB5MlutFSSlWSjKvY4JI8gER4qQvIyHqd6j3R4CFbwlvAZrqgrOc7m7u5zrnHGLQ2/cn1s172rmPkRn1UnlM0eDbgoSXCJB2EX/R7Pkp+mXAuYMq642+wptounrAMKyOWgScxgbeu2X+eozd1YU4llU85Mvbqd9SEqSoJSAOOAUjzRrZt65OdtV72rf8AkQJt+4/rZr3tW/8AIjHrfUzel5bw+ST7iqGxevXC9Xp1dcdm3nEuOJS2tKCUgADGNOA5xVb0+doe3mn1uVk3GJOmypIDmCrcRv4UojQErd0GTw8sRkmgXCP8W697Vv8AyIvqfJ3nTw6JClXVKB5O671EjNN9YOxW6kZGp49sZqyL7mt6WaXGe2Dxv+oNVi+KzU5dYcYemldUsahSUgIBHcd3PnjDDHDAjJG3rhCdLaroA/3W/wDIik0G4Rwtuu5/kx/5Ea3JZyb41SSSwywzpygz5IvTQrh+tuvD/wDGP/Ii4krVuuefSxKWpcDzqzhKU0t/j5SnERzS8y9OfoYkKAjtXoVWvN0TZfM1mdbU25XpvwthChgiXSkIbP8AOwpQ7iIi/Yt0aK3VKgxV9o0saZS2zviklYU/M9gcKSQ2jtGSo8NNY7DYaaYZbZZbQ022kJQhCQlKQNAABwHdHDqb1JbYnXRU48srPCKYqPZCjjOkUPPdBCz2RAPzQvNBBFGABHdBBrmCKUIIIO6ACCAwRCjghCDlAgydIUVcop4wAQQeWCADlBBBAB6YDwgggA9MGBAIIAIIfmggTIoeINIIgAcRBBDHCKUAVAYBMGT2mCCBA1+qMGv1Rgg5wyUfjfVGAFWfXGA8YOcCoNe2KgSDnPuwgmKgkwMsDye2DXPEwHjCzEA8+WDj2ws6Q05hkqwP0wecw++DGB3xMgpwIeMw8QY7oABDhCDMAEA4wQ0+WKB4hYHMe5Dh4iZKLCeyHujshkQiYEYwO6HgQCHEKgxpwg07IIOcQywGB2QYHZ7kEHOAwIgHlBgdg9EVQZhkuBbo7B6IMDshwQIGBBBBAooDBiDWAD0wQ4IAUPEEEAGB2QsDshwQJgWB2QYHYIMw4DAsDHCDA7PcgggXAYHZ7kLA7IqghkYEAOyDA7BBDhkmBYHZBgdghwQLgWO6CHCgA0gxDhQAemCHBABBiCCADA7IWB2CHCgTAEDsEGB2e5Br5YIDAsA8vch4HZDghkuBYHZCwOyHz4wGBiLAgIHZDgIMBgp07IRxyEMxSrjrGRjgMw8+WKc6wwQTFAifLC0irEGIhSnEPnD7opVxgQUBGkEEAGfLBmCCKBZHfBnXTMBMJJzAnA9eWYDnhmACGBEyCjXPGFlXbDIMLGsZDAEq+qMLKseuMB4wiYGI/Gzqowj5TBmDWBBecw9eGTANYcMgUEOEYhBGCAwQAoIIIpQgMEEAEHkhiDlAZFxghmFABBBBAoQcoOcBgRlXKFDPCKYEGYIUECjhQQQAQcoIIFGfLB5DCEOBGEEL0QRCYHnvhQQQKEPJwYWsPjp2xSHMG1TpMXFaW0WuWxTrXpE5LUyYDKX35lxK1/S0qJIAwNVY80ayOl5df1o25+PO/FEV3lUpSZ6QlSqNULaaem7v7bU4neR1DU0ELKhzTuIORrkR1kxtL6OEy+Gk1Gy0FRwC9Tktp9KmwI62oQS93JoUpSbwzEdHXb3Wtp20Cbtqp0KlSDTNLcnkuykwtxRUl1pG6QrkQ4T5on/XEa/aNNs1TSa3akhb4bmG91M7TGGcOoJBwFtjUaA4zjQRsI3RppHNNpvKRtjnHIDMW9VqElSabM1OpTbUpJSrSnph91W6htCRkqJ5ACLpOOYiH+mQJ/5wdXMgHCgTMqZvcznwcPJ3849jwz3ZzpESy8GeMLJFl89LqcTOvtWfbsq1IIOG56qOK33PsuqTgIB5Aqz2gcI1qldLi+0PDwmUtifB4NobW0T5wtR9yNZ6Md1bPbXvWcm7/kWlFbSBTp1+X69qUcBO+SnBKVKBGF4OAkjTOvYUrPbL9o1MXKy8xalzyhxvsjqJgJPEZSclJ8oBjpkoQeNuTRGU5rOTXtkW2pW0SyLhrKLbdpc5Q2VKeSp8PS7q9xS0hCwEq4AEgpGMjU8YgxvphXY42lYs+gAKAIzOu6Z80dUWJYlrWZRZujW9SGJOnzb6332NVpWpYCSDvZynAAA4ADEe6Nntg6foHtkeSlMfJjSpQT5RuxKSOVfourxAz8xlCxjOfC3se9Avph3a0ytw2db53ElWPDXdcDyRGlFlJJW3eXkFykuuTVeJlzLltJa6rw4p3N3GN3d0xjGNI7wXs52d7qk/MDau6rRQNHl8EfeRvtjXBLjuaKpTlJrPY2SiTRn6LJTy0pQuYl23VJTwBUkHA9Mc27X+k3U7U2g1S3Lct6lVOUpy0sOTMxMOJKngMrACQRhJOPKDExbYb1ldnWzOq3GG20qk2A3JMAboW8rCGmwANBvEctACeAjibo/bNahtVrNdl35p/q5KmuvKnFqJU5POH6VvEnxsq31qyeWvGNNMIcyn2N1tkuFDudk7Adpg2n2GK47KsSVRYmXJaelWXCtLSwcpIJ1wpBSrzkcokQKxxMcMdDi73rV2qt0OpLXLSVeQZN9h3KSzOIOW8g+tVkLbOcHJSOQEdyVFbMpJPzb6iGWG1OuEckpGT7giW1quWC1T3xyR/tm2x2nswkG/VNTk/VphO/K0yWUOucGcb6idEI+yPkAJ0jmyv9LO/X3esp1LtukNZ0Q+FzBP84qRk+aIvlmrj23bYGVOTPg0/cU1kOKBdRJMBJUABpkIQMAaAq7MmO9bA2W2LZNPRKUS2qehwICXZt5hLky9jmtxQ3j5OA5CM8QqXvLLMMysfDwjm20elvcbL7XzTWvI1KTV+mP0x0tOpHalCyUq8hUnyx1PY910W87blbgt6dTNyEzolYBSpKgcKQoHVKgdCDwjU9pOwvZzfDRXMUVqkVBS0rVUKU2iXfXjiFkJwsEaeMCRywQDG+25Q6RblCk6HQ5FmSp8ogNsstJwEj+kniTzMarJwazFYNkISXd5OR5/pf3XKVGclk2dQlIl5hxkLVNujIQspydNOEeaOmPdKuFo27+PO/JiFbDXTpfbNTJitOSbdNRX1qm1TZSGUt9aveK97xd3y6R2ym5OjmD+u2zD8JJRvlGuvGY5NalOWcMjPZj0o7iu7aLQrXmrZoksxU5oMLdZm3FrQN1SsgEAex92OqgOOsaDZc5scrNZS3aD1jT9Ul0F9KaZ4K4+0kEArG54wAKgM947YkDSOayUW/dWDfCLxyzHV6aekKLPTzKUrXLSzjyUq4KKUkgHu0jjxnpi3ithDyrNoCUqSFAqm3RxHkjsG6/2LVb7ie/IMfPnoqScjUdslqSc/KS83LOIXvsvthxCsMKOqSCDG2iEWpOXkarnKG1R8ySmumJdi1D9BtvrHYmed+SYlvYl0jrev+rN2/Vacu3q49nwdpb4eYmSPYtuYSd7Gu6pI7iYkaq7NdndRly1O2LbMwkgjC6WySPId3IPeI+eu26lSdl7Vrko1vPOsy9LmguSWh09ZLqCEOpAXxyhR0PEYHOKo12J4WA5WQay8nenSB2gzuzXZw9dFOp8vPzDc2wwGX1qSghxe7nKddI1noy7ZKztWerqKtRKfTBTQwW/BXlr3+s3853gMY3R6Yw3TEm3J3o0InH0BLr8zTnVjHBSlpJHuxpf9j7OZi8SBjxZT/3IwUF02zJ2PekSvt8270XZitFJlZH1auJ1sOiSD3VIZbJIC3V4O7nBwkAk9w1HO9U6XO0Rc2TLy1ryKBxZWyt0j+cXE+9GidJIVRO229EVAuCZVOZaKiR9LLaOr3TyG7jXtzHYOzHahsHdocnSreqluW+3ugIp002iSWlROo3VgBSieYJyddY27I1wUsZya1KVk2s4wRFYnS7rMzWJKnXFZ7E41NPIYS/SXz1pWshKcNKGFZUQMBQOvPhHXqVjdyTjHGNHe2XbNqjc8hd0vbNHRVZN/wAIZnJNtLe+vdIBXuYC9Dnxs6gHkI0npmXlOWnspRTqW+5LTlemxI9e2rCm2d1S3SDyJSncyOG/kaiNDSnJKKwblmEW5PJrm1jpVUehVFyl2NTGbjcaO67UHJjclARxDe6CXfKMJ7CdYitrpd7QRPZXL2ytve/SAwsK8m91n9EXfRD2R0a+5qfua5pdM3RKY6JRiQUn6XMPbqVEr7UJSoDd4EnXhr14/ZlpO0YUZVrUQ00I3BJmQa6kJ7NzdxjzRum6qntxk1R6ti3ZwQ7sX6TVGvGry9BummN27UplwNSjyJjrJWYWfWo3iAULJ0AOQdMKycR0GIiazdgdg2ttDcvCl04pUlA8Eklnel5NzUKcbB4EjAH1OuMZMSzHPY4t+6dENyXvGtbUrimLR2dV+6JWWbmXqXIOzSGXCQlwoSTgkajOI5Ue6Yl3NDLlmUBI4ZM66B+THR/SPUBsGvfP+ZJn8gxyb0LqdTaxtpflKpT5Oel/UGZX1Uyyl1G8HpfBwoEZ1OveY21RhscpLsarZS3xjHzNjlumNdjjgzZlBcHMIn3QT590+9E47Dtvds7TJg0hcq7Q7gSgr8AfdDiXkjippwAb+OYISoccY1jaazsu2cVOVVLz1iW08hQIyKa0lac80qCcpPeCI4BKl2RtoDVBm3Jk0S4wzKOJVlbiUvhG4SOJKSUK7cmMowhYnhYaMZSnW1nsdldJrbFWNlLVEXSaPI1M1JbqV+EurQEbgBGN3yxnujxtDqG03Z4m5qlIS1PmDOvSxZl1qUgBsgZyrXXMQ/8A2QJCDK2jkfu0x+SmN16DKUjYaMD/AAvN/lCMXWlUpGUZt2OJHF29LK6qLddao7FoUR1mnVGZk0uuTToUsNOqRvEAYBO7mMOnplXUVAC0bdOeQnnPiiK6vLod6QM62tCVtuXw4haVAEKSaiQQQeIIOMR9B5mxbJmGFszFn2+60sELQumsqSodhBTrGc1CtLMe5hCU5t89mQbsw6WFArtUapd50hNtOPKCW55M110pk8AtRSlTevMgp7SImfa/dczZOzStXXJSrM4/TpfrkMuqIQvUDBI15xxV0uLMtmy9qLMlbcpLyUnUaamaekGhhthfWLQSlPsUrCR4o0ylXbE4VysztX6Bi6jUXVuzS6EhC3FnKnN1YQFnygA+eMZVx92S8zKFksuL8jRF9MS7Uars2gJHfOuj/lig9Mi6eVo26f8A7935Mat0RKpZEhfVbXfU1b8tT10xIYVWFNJbLvWjRPWab2M8OUdPi5ujqf8ADWzH8NJRnZ0oSxtMK3ZJZyYHo0bcqvtYrdbp9So1Np6adLNPIVKPrc3ytShg7w0xu+7Gqbbuktc9gbRKzbUlbFJnZanhCkvPTDiVqCmws5AGOZie7CTYc5KO1axk269LOK6lyapCWShSk67hU3oSMg4zpmOG+mE2Pn2XWr/UtfAJjCqEbJtYMrZyhFM+gVImVzlLlJtSQlT7CHSBwBUkH+mLqLC2v2OUz7ja/IEX8czOldjnjpEdICvbM9oTdsUy3qXUGVU5mcL0y+4hQK1uJ3cJBGPpfuxLlg3TMXNstpF3uyrTExUKWieUwhRKEKU3vboPHHKOPunQM7dmv5BlfhpiOn9hA/8AhytI/wDy6z8DG6UUoRZpU25yXoQVafTEqUxWZD5prUkJOjOqHhUzJvuOOsII9eEEeMBoSBrjOMmOupOaZm5ZuZl3m3mXUBbbiFZSpJGQQRxBEfKSiy781LS7MpLuzDvUhW40grVgJyTga4ABJ8kdOdDvbB6jTUvs7umcHqbML3aPNvOaS7hxiWJ5IUc7hJ0J3eaRG23TrYpRNNWozNxkSv0mNtNZ2U1GgSlJokhU/VRqYcWZp5aOr6otgY3Qc56z3I3fYNe87tF2Y067KhIS8hMzTsw2thhZUhPVvLb0J113M+eOef7IQQm4LJJH71n/AMuXiVehas/Q80PH8Lnv/VuxqlBKtPzNqsfUafYietdLi7ZGrz8m3Z1DW3KzTzAWubdBIQ4pGTppnEY1XTKupJ1tG3fx934oiO2X5FjbfLP1dyWapyLnWqaXNFIZS34UreKyrQJxxzpHbXzS9HZXrq3swPlmJL4432quCXumuuU5t89iJdmHSpuK7doVCtqatiiSzFTmxLreZm3FrQCCcgEAco6xjQLOmdjVbrKWrRdsSoVOWT4QlNM8FceaSCBvjcyoAFQGe8dsb/HLY4t+6sHTBNLllLq0NNqdcWlCEAqUpRwEgcST2RyztI6WjcpVn5KxqFLT8izp6qzz6kIdOuS20Bko4YUpQzrpjBM0dIo1E7ELwRSQ6Zw0l7cDWd8jd8bdxrnGeEcOdHi4LHou06VqO0CSl5qiplXEsF6W69piZKkFt0owcgALAONCoHlmNtMItOUlk1XTkmlHjJvEv0vNoKJrLrVrzLedGksrQT3b3WH3onjo6bd3tqlTnqNO2y9S6hIy4mHHmHuulVIKgkDeISpCyd7CSDkJJzyG50i4tk9/SblPp9UtKvMrR9NlN5l3xT9U2dQPKIyth7O7Qsd6ou2tRJal+qLiXZhDAIQSlOAEjgkdw0yScaxjKUWu2BGM/UhzpF7fbk2abQ2LZpNAplQZcpjU6XZl5aVBS3HUbvi8vpfuxMWzG5pu6dl9Fu2blmmJmo05E4plskoQVJ3t0E64jkvpxpSNuUqf/l2V/wDUTMdL7A1AdHS0Tn/F9n4KM7K0q4y9SVyfUlF+RCdidLio1C4aU1dNuUimUWbWlMzOMTTilS6VDRZBGN0EjOugyeUdZBaVDKSCO0R8mpNRcpzDQQVgS6d4AZ8UJ1J7sR3H0MNpbl22S5atXmS7W6AlLaVLWSuYlDo24c8SDlB48AT66MrqYpKUTGq6TbUjoIrQkEqUABzPARyPfnS3qUhcFUbti2qVUqJLOKTLTb004lcwlPFYAGN0kHd7Rg843bpmbTXbSsxFq0iYLdbr6FtlSFlK5eUAw44McFEkITw4kj1scQToU3S321NqbBlypAKceKU6Ed2OEKaU02yXXNNJH0m20XbP2Jsvqt2yMmzOzMihtSWHlFKFbziUnJGvBRiOejXtxru1O6KrSKrQqfTUSMkmZSuWdWsrJXu4O9542/pV4PR5uXI/cGfhm4gjoEtpG0a5Duj9aG/hoxjBOty9CylixQ9TsUZ3eOsctbYOlDctkbQrhtmStakTcvSXw0h56YcStY6tK8kAY9ljjHU6tAeEfN3pTj+/hfn3UP8A07USqCk3kysk4rg7q25XvObP9ltTu+nyLE9MSapdKGHllKFdY8hs5I1GN/PmjRujTtorW1WsV2Rq9Ep9MTTZdh5CpV1a9/rFLBB3uzc92L3piEjo4XB9tJf+rZiH/wCx+qJuu8vuCT+EeiqtdJy88kc31EjsHMMDOsKGmNBuLC5KtI2/QJ6uVN4MyMiwuYfcPsUJBJ96OQT0wrsSUuvWPRwxkKWhE471gTxIHi43se7EgdOe9k0+0qdYso/uzVYdExOJScESrZ0B7lObo7wlQ7YgSb2WTbXR8lNp5ad3nqmUraKThMifpaHcd7oBz9SoGOqmqLjmXmc11klLEfI75pU/LVSmS1RkXkvysy0l5l1JyFIUMg+gxzbth6Slw2LtLq9qSVt0acYkFNhDz824hat5tKtQBj2WIy/QfvVNUsecsudf35ugub8sFqJUZRwkpGvJC99OOQ3RppE0VWzrQqk85P1K0qDPTbuOsfmac044vAwMqUkk6ADWNe1Qm1JGSzKOYs5XR0v7tUPFsygHyTrp/wCWGemBdoODZtvg98878mMD006LSaJtLosrRaRT6XLrowcW1JyyGUqV17gyQkAE4A1ieOjfY9l1TYja9QqloW/PTr0oS7MTFMZccWd9QypSkknzxvaqUVLb3NcZWOTin2M70bdqM/tTtSp1ip0uSp7snUDKJblXVOJUOqQvJKufj480aRtg6UNDtirP0Oz6W3cc7LrKJiaXMdXKNLGcpSoAqcUOBxhI18bIIjI9KCuSWy/Y+/JWfT5KhzVdmxJIVIS6WA3lBU66AgDx9xG6DyJHZiIM6JeyWl7QatO1u4mg/QaStLAkgSBMvlIVurI9glJBwPXFQ4AEHXGEeZvsbJTlxFdz0X0s9onqgD4Na/VZ/U4l17/k3us/oiXdjfSWot3VRmh3TIIt2pzDgblnQ+XJWYUeCd8gFtROgCsg6YVk4iZVWTZyqP6jfMpQfU3d3PBPU5rqcdm7u4jjnpUbJaXs8uCTqNCY6u36yFtiVJyJV9IyUJJ1KFJyQPY7pHAgCx2WPbjBhPdBZ7ncyGirjpHHqelvd/VhZsugpB7Zx7T/AIYnPoqXvNXrskk5iqPF6p015dPmnVHKnSgAoWe9SFIJ78xxlsKTJTu1mz5SclmJqXfqCUuMvNhaFgpXoUnQjyxaK4vdvXYxtm1t2eZLA6Xl1ZwLPt5XcJ53P5MSLsl6Tlv3ZWWKDc1L+ZuozLgalXRM9dKvLPBO+UpLaidAFDB08bJxEpVCwLBnpYsTVj2y80dd1dKYI/JjhLpI2fRrT2sVigUBoNU4sNPoYCt4S5cRlTYJ1wMZAPDMIxhY8RWCuUo8tn0XCs8OUONY2TVCcrOzG2avUAoTc5S5d57eznfU2Cc98bPHM1g3IRghkwhAooPLDg80QgQQeYQtOyAH54OfEwd8LOkUuAPfBBmAeWDKEEBggAhwgYcCMfKKYq5RTABBBBABD4wofCAFBBBy5wAQQc4OUAEEEEAEEEPEAHGKk6KBJ5whGPuWdnqdb9QnqbTnanOy8styXlGyAp9wDKUDJA1PfAhz3WOiRS6jVJ2orv2qocm5l2ZWkSDRAU4srPE54qMa/cPRCnJaQdmLevbwyZQglMtOU4IDpGoSHEL8XPekxH9s7fdrVjT7tOrc6uedccU87I12VUh1ClKJVuE7q0JKs4HjJAGEgCM7c3Suvio0OZkZWk0ahuvIKDONvLdcbBGCUhQACuwnODyMdSjascmputrsa50UL0qFsbUqNJyrziaNXnhLTkqVYbKlp8R3d4b4UEjI4gkHlE49KeubYKTdlGa2druFFPckFqmjTael9HW9YQN4ltWDu8oizojbNavXL3pl3TtPfk7doquuYdebKRNvBGG0tgjxkje3ivhkAAnXHbqjvDGsS5xU+OS1puPJwpMXv0oG5Z1Tb98FaUEpBoTZycfxGY7ak2U1S3WJeqy6JgTMohE00+3kL3kDfSpJ7dciL8J1iOeka5d7eyWqsWPT5ubqkzusrMovDzLBP01xABBKt0YATqCrI4RqlJSfCwZrMVyyM766JFCqE0ubs24XqElRz4FNsGaYT3IVvJWkdxKh2YiGdo/R/v6wJJ24HGJSoyEnla5+mvFLsukDVxSThSUjtSVY4nA1jLWh0mNpdr/3IrIk66tgbpbqiFMTaOwLUACdPqk57SY9NpXSauu6rTnqB6i0ihy080WJh9uZW64W1DCkpKgkJJ7dY3xVqeO6NMnW1nzNz6HO1i46jdDlgXHUn6rLLk3JmnTUy4VvsqbKd5oqOq0lKiQVHKd0jUEY6vC8Ea8x78ckdC3ZjXZe5ntoVbkX6fJtyjkpTmZhpTbj6llO+7g4IQEpKRkeMVEjQa9abqSoeURptUdz2m6vdtWT52UBY+iDlcq43uP/APImPo4tORoI+adIeaHSGk0B5G/83CPF3hn9ceyPozWa1JUWiT1Yqb6WJKSYW++4ogBKEgknXuEZ38qP4EoWHJv1OSunjdyp246TYcqs9RINiozxB0LywpLSP5qd5R+3T3xadGnbJs92X2G5S6mxWHaxOzjk1OuMSwUjOiW0JOdQEJT5yYjixJec23bc2UVF3x63Oqnaj1S8liWSN4oBGMYQEtBWh1zxjq0dF3Y7nJo9U89WmPlRlPZCKgzGKnKTkjkbbHWqBcO0mqXFZS52SlJ9aJxO+31LkvNZytScHTxkhwKBzvKMdz7PbrG03Yi3WpbdE5P056XmGkn9LmglSHEcvZg47QQeBEQ/tx6OtnUHZlVq3Y9On26vTkCZ3HJ158OsoOXUBKifG3MkYGcgDmY0zoNbQ2pC8qhYcxNsmVq6FTkketGky2AFIA+ybGf/AAzxzoscLK0490SCnXNp9maD0Wq/IW/tmtabqa0sMvb0mtTh3Q0txspTnPDxsJ8pEfRBZxwOscUdKLYXV6ZX5+87TprtSo1QcL07JyzRW7KOK9eoITqttR8Y4GUknIxqMJs+6Te0G2qQ3SZpNPuViXT1bS55xSZhAHJbicleOHjDPaTCyDuxKIrkqsxZMHTauy67Up1szNsXJU6QqamnWnhKuBIWA3vDOnaPdMbl0Ra7Xbl2NSdVuCrTdUnlT802qYmV7yylLpCRnuAjkza1tXuna7OU6nT1Kk2/BFqdlZKnMuOvFZTuk81KGOQSI696Jtr120tjMhS7jpzlOn1zkzMGWdKStCHHSpO9gkAka44jOusa7a9kFnubK5b5cdjhqi285c20gW6ibTKLqNaelUvqb3w2VPKG8UgjPkyInr6DStJVlO0Gmny0df56ICk7lFsbSXa1LqllTVNrT8w228rxVKS8vAOucRMv0YF5nhTbZ++X8qOm1Tljps0w2Jy3rzJc6PnR/qWy+/Zi5py6JSqpdprkiGGZFTJBW40veyVqzjq8Y74n8GONrR6Vt41q8qFRXadbvU1Gpy0m4WisrCXXUoJHjcQFEx2QrjHDbGSl73c665R2+6Y+7D+herfcT3wao+Ymzqs1+3q1S6va5dFYYbHg3VS3XryW8HCMHOhPKPprdysWvVjn94v8/wDVqj59dEB9C9u9ptpeQVAOeKFDOjCo26eSipZNF6c9uDLV/bht3ZlQip3FWKU09lCVrozcsVnGoStbQ1xr4pzFXR32Pze1evOVirTyPUCTm/7oqW/vzU25ostkZ3gFZ8ZajkgnGTqOztr+z6nbSbDnbbqO4h1Y62TmSnKpaYSDuOD0kHtBI5xxLsQvie2K7V3pe4+sk5YueAV2RUrVrCtHQn2W4dQR65CjjORGcZ74tQWGYuDjJN8o6d6baAjo/wA6AAAKjJYAGg+nJiP/AOx+Y6y8D3So+EiQumw4w70eZ2YbebWyqekVpcSoFKkl9OoPDGDxiPf7Hw7LuOXl1TiHMCVzunPJyNcfkyNjji2JNO2LYtZ+09Lc1Vm35CrtIDbVTkylLwQDkIUCCladTooaZOMRzzcvRFvOUZWaJdFGrI5NzMuuUJHfq4P++UWW2zaTtosLbVWa+Ez9HpTjgZk5eYbL9NmJdOUoUT60LVqo4KVDODkcbqS6Yd3CWSl6zaHMLx+mJnHUA9+N0+/Fh1Yr3WLOnJ8oiqVq20jYtd6pCXmJ6g1OTwtdOcd35R9CtRlsEoWhWD4ycHjqCDE39MurC7djtgXtJNOJk5yYS6RjIb66XUUg+cERDdanL129bSVTclTUTlXmEIlUIlUK8GkmklRT1i9d1I3lKJOp1wCcCO4KpsroVT2LM7MZtazJM09qUamAMrbcbA3HU55hQB9yM7ZKEot9zCpOaa8iJegBW5aZ2fVu3esQmdkqoqaU3veMpp1CN1eOzeQoeaOmU4Aj5wVuj7RNhF9tzyw9SZ2WUUy9SabKpOcbUdU7x8VSVY1bUQoEZ4gKiRl9Ly+jTuqFs2+mZ3MCa610pzj13V/0b3njCyhylujymZV3KKxLho7ZyM4yMwjkxxL0b7q2w3htobuiVmZ2qSM39KrL8zvIp6ZcHRKAPFC0n1gTlWqt7QqMdt5zGicNjwdEJ71kjvpJAnYNe2v+BZn8gxwHsxuW77UuZdTscTKqsZRxlQYkjNK6lSkFR3Ak4G8lGuO7nHf/AEkUhWwa9+X9xZn8gxyr0Diwduc0GXkOfoems7qgcfT5bsjfS9tcmabouVkUY6pbU+kRWpRdPU9dDKHgUL8Dt9TTigeQWGt5PlSQe+Nv6N3R6uSYu2n3Xe1Mco9Mpr4mZeSmceETbqTlBUnJKEBWFeN4xI4Aans3HlgMYPUPbtSwZKhZy3k5S/sg6imStE4/dpj8lMbl0FHf7xYyP8Lzn5QjS/7IO603JWj1riEDrpjG8cexTG4dBYpVsK3kKSoGsTeoOc+MmM38lfia+VY8HI16z78ntguObk8+FS10zj8v4m99MROLUjTn4wGnOJJf26dIB5Cm0eqDRUCN5u21byfJlBHpBiOKo639EXONdYjf+bhfi72v64dkfTJvmd0cTGyy+KUU1ngxrqbcuWuT59W7so2tbXLpVU6uxV2DNEeFVqssqaCEjQBDagkqxyQkBPeI6d6QlAk7b6LFeoFNbKJKnUluXZSeO6hSAM9+kTZEZ9Kfd+h+vEr4Cnn8oRo6rnJeSN6qUEcSbCtls3tWuKo0aUrTFIckZRM0XHpUvBwFe7jAUnHbnWJkHQ4rwGl/0vH8kufnYhjZJtUm9mFdnqvQ00uafnJYSy0zK/FCQreyN08Ykk9MG9eVOtkedfyo6bY2qXuvg5qnW4+8ufwOnej5s5mtl9huW1N1VipuLnnZrrmWC0nCwnxd0qVw3e2OM+mI9/fuutH+raH/AJCYn/oy7fLj2n37ULfrEpSGmJelqnEKk97fKg62jByTphfvRzv0u1Mnb7c7Tr6Eb4ZBBWARllPbGqlSU3nubLmnFY7H0Htdebbpmn7zZ/IEZOOE6b0s74kpGXlG5S2S2w0lpJUFZwkADPj90bXsx6Tt53RtDoFuzctbwl6jOol3SyFb4Sc5I8bjpGuWmsXJsjfF4RqfTnV/f3bx/mGV+GmI6j2CpCujlaQP1us/BRy3053Jdjbwz1zqEZoMrjeUBn6dMR1HsKcCejlaWB/i6z8DGU/lwMYL+JLP0OL+iihI212RkAhbqgQRxBlnI2zpY7H07P6sqv0GUzalTd3SyhPi095X7npwbV7Hhg+L9TGjdFKbSvbvYzSXUkpmVgpCtdJZ0cI+idxUOmXHRJujVmUbnJCcaLT7LgylaTGyy7ZNOPoa66d0Wpep85to20OrbQbetWVr5W9UqC1MS65snPhTbhaKFK7FjqyFcjoeZEdjdCtGOjxQx2TU9/6t2OQdt2zif2U3eujTzjj9LeHWU2oOJwJhvPrVHh1qeChz0UAAcDr7oVrSvo8UMpUCPCp7BB4/227C/b004ihS6j3HFqKP80G1N6325lEsupXA/KJeU2VhsrmVpCinIzjPDIieT0O64BptCpvtMv8APRzzNV/5ndqU5WpdyWVNU6vvzLaHVeKVImFqAIznETAemDfR4U62fSv5UbLJTeNjNcIwTlvXmTL0ftgVT2X36/c05dUrVku01yRSw1IKZKd9xpe9vFauHV4xjnHQAyRqY4wsvpWXrWbxodHfp1vFqoVOWk3OqK98JddSgkeNxAVmO0E98cVqkpe8dlTWMRKHGw4kpUAQRggjjHOm0bom2nXp5yoWpVHbVfcVvKlkS4fk8653W95JRnsSrdH1MTRtVmbjldnVdetGQVP10Si0yTKVBJKyMbwyQCRkqxkZxjnHFtl9IHahs73aDV3FVRLAwmSr7a25pscAAs4XjQ+uCu44GIzqhOSzExscE8SPe+ejDtDtuWVUJJFPuRiXHWEyJLcwnGuUtr44xnRWewGM50SNrtwSl+02zatWJuq0Wr7zUsmadLq5Z4JK0qQtRKtwhKgUkkZIIxrnyuTpb3pO0h+Xkbao1IfcQUicMy48W88wkpSM+U+mMV0O9mVcq9/0u8X5KZlLfoxU6zMOoKRNOlBShLefXJAWVFQ00ABOuOhuTrfURoSSmumy66dTuNuUqP8A5dlv/UTMdLbAQpXRztL+QGvg45f6djrLW3OTLriEZt6WxvED93mI6j6PZSro5WkAR+sLQ/8ALjVY/wCHEzgvfkzi/on06UqW1+3qfUJdEzJzkq+w+y4MpWhTCsgxlpuQrPR827s+DOuzSJFSXGVL8Uz9PdOClR4b3ikZ4b7YOANItOh+9LHbdaKEvtKc3HAUhYz+kK5R1l0odlMztKtOVdoSJVNxUx4LlVPq3EutK0caUvBIBGFDT1yB2xtlNQmlLs0YRhKcG13ycvpk5/pCdIN3rFvS8tPKKlDiqTprJAwOQUd4duFunjjXCdK+UlpDbFdMnKNIZl2Gmmmm0jCUJEugACOtui5sqmtm1szs1X0SxuKpu5mOpXvpZZRo20FYGeaie1eOWY5H6YTradut2oU8gKPVYSVDJ+kI5RFYnNqPZIOuSinLu2dhdKRwvdHe5+rBJRKNOHH1KXEKJ9AMc/8AQLqDSNqldk1uAOzFF32xjiEPJ3vyxHW1WoclclnzVDqSC5J1CSMu8kc0rRg49MfP6u0O+9hG0RmaW45JT0k6fAqkGiZWebIIxk6ELSDvNk7wIPYFRjW04ygvMzmsSUz6QE+KY+b3SacbnNtd9LlSHgue6tG5rvKDLaCB37wI8sSFW+lpfc1R3JWTo1DpkypG74cla3CjtUEKwkHsySB3xiujDsnrN9XxT7mqsrNJt2QmUzr83NBWZ95J30pSVaryvC1L1GmNSTjKuPSTlIxnLqNKJ0l0yEqHRyuJI4hyRB/HGYh/+x9tq+aq89NfAJP4R6Jo6YpbR0drkUtSUpC5PJJwP1WzHG+yPa1VNmNQqU7b6qS+5UWmmXhNHeADZUU4wofVnPmhVB2UtLvklktlqz2wfSDGITh3UlSlBIAySdAI4iX0u784+DWvn7Rfy43KtdICq1XotVS4qk5IStcqlTdokn4ISlKUlKSpzUnVKCs9md0c40uice5tVsZLggHbjeg2hbVqtcCZlbdOcdTKSToSVFuVbJSlYTpnOVuAaZ3vPHR8z0htjU3Ya7INLriKOun+ABkSAwlrc3BpnGg1iL+iZsgoG0x2tVW40PO0SnhErLty0wprfmDhRJUkg4SjdGOB3zngIn4dFzZAk59Sqr7bP/KjbY4JqPoa4KfMvU5L2IXiNnu02k3E8+pcihSpSoObpG/KuEBSyO4hDmNfW44x9H0JCkBaVJUkjIUDkEdscM9K3ZLRNmczSapbyXWqBUUqlXWpl9TpbmU7ys76ySQtHLkUc97ToPoi3+q9dkcvLTUyH6nQ3PU+YXvbxcQkAtOd+UEA/ZJVC/EkpxLRmLcZEKdPIhG1OhnGvqGPh3In7osr3tgdp/civhFxz3081tI2pUAvOobBomm8oD93cjojortI+h/tMpUFDwRWCOf0xULH/BiSC/iyI76esg/MbPrdn20FTMrWN14jgnrGVpST5wB5xHj0CapJqs+46BvoTOsVITnV58ZTTjSEhWOzeQoRPd+WzSbxtGo2zWWt+TnmtxRA8ZtQOUrT2KSoBQPaI4Huig7RNh18oqHWTFPfliRK1eXbJlJtpXsSTlOFYG80vUEZHBKokGpVuHmJpxmpH0SzjSOYuntUpNdGtahJeSZ7wxyeU3zS0lpTe8ezKlgDtwewxo6ulnfXqUGjb9veFbmPC953c3vqurzjHdveeNDtag7RtuF6OVHM1OuTagJutTDeJWVbBxhJ0Sd3UJbRrnjjKlRlXVslukYznuWInQ/QRp01LbNKvUHAQzPVtZZ+yDbTaFH74EeaOObKnqvTKlSajQFPiry60uSfUs9cvrMH1qMHeOM6YMfTiw7apNo2pTbaozHUyUg0G2wR4yjnKlq7VKUSonmSY+evR0blztosdLT6FYqKRosE+sXGVUs7pEnHG1GyVLbDt9k5XrKnXK5TWFKCOueoDTAKjnCQtbIGePDXSPHYrsyq+2G5p5c3XQ3KsuIcq86/M9bOOBf1KVHeJUAQFq0GOeMR3Ff9qUy8rPqFs1lvflZ1ooKsZU0saocT9klQBHkjgqzbkruwrbCo1loofkHDJ1WVQvAmpZRBK0Z9cMbriPJjTJiwtzF7VhiVfvLPKPojKS7ElJMSUo0lqXYbS00hPBKUjAHoEVxZ0eoSdVpsvUqfMtzUpMtJdYebVlLiFDIUD3gxdxxG/IawQGFAoc4cKCAGYUEEABgGeyCDEAEEEAgAgMGgggUIcKAwIyqFD5RTAg4DBCiAIfkhCCKUBBBzgGsAA8sEMwDjAgQQQeeIAggggAEMawoBFBj65QqHXZYy1bo1OqjCuLc5KoeSfMoGMJTtmezqmzaJyn2Fa8pMo1Q6zSWErT5CE5EbZBDIKUIQgBKEgADAAHCKofPjC78wA+MLEPhBmAMPcFrWzcLYbr9u0mroByEz0k28Af5wMWNF2fWFRJsTdGsq26dMgYD0tTGW1gfbBOY2YQicmKmEh8IB6IBrBENi7GNFu0EPiY9RKZ1wX1gcEo3vb2c72ccc65i/mJWXmZdcvMsNPMuDC23EBSVDsIOhj1B1irzwbIWNPolFp8yZmQo9PlHykp6xmWQhRB4jIGcaCL8wHhCjEZBaUqSUqAKVDBBGQR2RjWLdoDD7b8vRKYy62coW3KISpJ7QQMiMmCBDzzgUQSBGu1yw7Er0z4VXLLtypzAGOtm6Yy6vHlUkmMVtb2mUDZlS5Op3HL1BcpOPFhDkqx1gSsJKt066ZAJHkMbhIzcvPSLE7KOpel5htLrS08FJUMgjzGLyE0WVu2zbFutFq3rdpFIQTkpkZJtgE9viARliomI7t/a9a1eu+4rbpKJ+Zet1lx2oTCGPpCNw4KQvOqiQoAfYK7IvNmW1C1toFoTl1Ud5+Xpck8tp92db6ncKUJWpRycboChrBpl3I2Rdu2+slS6FS1KJySZRvJPoik21bX1vUn8Sb+KIYq3Sz2VSc64xLqrU+y2cKmWJPDYGdD45CiDyONY3yX2uWfObLJnaTIzM1M0CWCi44JZSXMpUEqASrBOCfJFcZIwyjbG7dt1p1DrVBpSHEKCkKTJtgpUDkEHGh74ypyTGvbO7spt72lI3RRw+JCeSpTPXN7i8JUUnI5apMYnZ9tQty9ruuK2KQ3PJnrfdLU6X2dxBUHFI8Q51GUKiNMq5N1caS4hSHEBSVAggjQg8QRFhJW5QJKYRMSdDpks+3qhxqVQhSdMaEDI0jA7V9plrbM6dJT1yuzITOvFlluXZLq1EJKid0chjj3iM9Z1w0u7LYp9xUV4vSE+yHmVEYVg8iORByCORER5xkzSWcGWAjHTlAoU5MLmZyi02YeX69x2VQtSscMkjJjWhtPts7WFbMwJz1dTLmYP0n6VubgX67PHBjc1LONOZiNNFyi2epVLepyKa9TZNySQEhEsthJaSBwwkjAxyimm0mlUwrNNpklJFzAX4OwlvexwzugZjR9n+161r3TcKqKmexQN7w3rmNzhvZ3ddfWGNDa6XeyJagPCauCf9hVFUZN4Md2Se5mUl5pstTLDbzZ4oWgKSfMY1B7ZHstffU+7s5tNbiiSpRpDHjE8z4upjH7LNs1m7SK5NUe3PVEzUrLeEu+ESim0hG8EjU6ZyeHceyLrZTtXtbaVRqlVrc8N8Gpywh4zDHVkko39Bz0g4yXDKnF8m4UikUujyiZSk02Tp8ung1LMJaQPIEgCLzOsaHsk2t2btPl5tdszjxelN0vS8y0WnQlQ8VYSeKTqMjmDFdZ2o2zSdqdM2cTRm/VypspelwlklrdIcIyrgP0pfoiYZU15G5zkrKzjCmJyWZmGVaKbdQFJPlB0jUvnT7LvCPCPnc2j1u9vbwo0vnPb6zjD2mbTLP2dU9qcuqrIlC+SJdhCS4+9jjuNpyogZGTwHOI6tnpXbJaxUkyT89P0oLOEvzkvhryqUkq3B3qxFUZY4GVknKXlZeVaSzLMNstJGEobSEpHkAj1AhNLQ62lxtaVoWApKknIIPAg8413aDfNrWFRxVbpqzUhLrVuNJIK3HlYzuoQnKlHA5CMVyXhGfmmGJmXXLzLLb7Lid1bbiApKh2EHQiLSn0WjU98zEhSZCUeKSkuMSyEKweIyBnGg9EQnSullsln6t4C5OVKRQTgTMxKHqvKd0kpHeQIlS676ta17XFy1utSkrSlJSWpjf3w9vDKQ2E5KyRqAnOYycZIx3o2iFiIApnS22TzdW8Cceq8s2VbomXJMlHlKUkrA8qdImGrXfQpCxJq9UziJ2iy8kqe8IlCHQ4ylO8VIxx0iOLXcyUkzJVKkUqp7nqlTZOd6vO54QwlzdzxxvA4j0p9PkadL+D0+Tl5NneKurYaS2nJ4nAGMxruzC/7c2jW16vW1MuOy6XlMOtuo3HWXE48VaTqCQQR2giLPa3tQtTZhR5ap3PMPpTNPFphqXaLjiyElSjgexAGp7xDD7DK7mwOWzbq5kzK6DS1PlfWF0yje+V5zvZxnOdcxlUpwI0XaftVtfZ3b9KrlwCe8Fqjgbl/B2C4rJRv6gcNAY0KmdLPY7OzaGF1Soyu8cdY7IObqe8lIOB3xdrfJMpE8cDHnNS7E0wqXmmGn2VjCm3EBSVDvB0MaTtG2qWnY9kyV5VGZdnKPPOttyz8gkPBzfQpaVAg4KSEnWNspVSZqNHlqowlYl5lhL6N4YUEqTvDI7cGJhjci3Nt26eNApR8sm38UUKtW2VZzb1J/Em/iiPqb0gbAqGzir39LOVFVGpMy1LTSlSpS4FuFAThJ4jx06xrjXS02TraLodrG4nirwI4HnzGSjN9iNxXcmym0KjU15T1PpUjKOrTuqWxLoQojjgkAaQ5ug0OcmFTE3R6fMPL9c47LIUo+UkZiPLU29WFctmXDdtLcqC6bb6AudK5YpWARnxRnXSNQd6XmyNtRSp2tBQ4gyJBHuxNsi8E3C2rcHCgUof8A2bfxRWzQKEw8l5ii01p1B3kLRKoCkntBA0MaTSNs9n1TZRO7S5bw/wBQpNa0OlTGHcpUlJITnUZUI0trpa7IlvhlyarDRJwd6nrJHmGsVQm+wykTRUKFR6jM+Ez9KkJp7dCesel0LVgcBkjONTF3LysvLyqJaXYbaYQndS2hAShI7ABpiLCz7loN3UFmuW5UmKjT3iQl1o8FDikjilQ5g6iMsrQZjF57FRipS3KBKTDcxKUOmS7zZyhxqUQlSfIQMiMsOERVfe3mxrL2gS1l1p6abnnup33kNAsMdarCesVnxeRPYCDEnqe3UFSuAGdINS8ybkeVSpdNqaEN1Knys6hCt5KZhlLgSe0BQODFchISNOlUytPk2JOXSSUtMNhtAJOSQAMcYgUdLzZGAkrerLe8MjekFcIkzZftUsraTLPu2pVxMuS4Bel3W1NPNpPBRQoA7p5KGkHGWAmjPrte23Flxy36UtajlSlSbZJPfpDTbFtgaUClD/7Nv4o0/attpsLZs6mUuGqqVUFIDgkpVsuvBJ4KUBogHBwVEZjCbNukfszvisM0aTqMxTqjMK3WGJ5rcDquSUrBKCo8k5yYuJYyTMcknt27b7TqHW6HTELQoKSpMogFJGoIONDGSOY0aR2pW1ObWpnZmyie9W5ZhT7ilM4Z3QlKtFZ10WI9Nr+0y3Nl1BlazcqZxUtNTPgzfgzPWK39xS9RnQYSdYmGZcYN0zGOrdBoVdllS1bo1OqjCtFNzkqh5J8oUCI1TaltVtfZzbdNr9wJnTJ1FYQx4OzvqyWy5qM6eKDGA2ndICwdnlel6LcLlRRNzEm3OthqWKx1ayoJ17fFOkVJ+Ri5G303Zhs2ps2icp+z+1ZWZQcodZpDCVpPcQnI80bUG0JSEoQlIAwABgCIAX0udk7Rw65WkHiAqQUI3XaFtwsmxWqM5XTUEprEl4bLdVLb/wBL8XO9rofGEXZLOCbotZN3qVvUSpTAmKhSJCbeCQkOPyyHFYGcDJGcan0xfSUpLScqiVlmGmWEDdS02gJQkdgA0AiEJLpW7KJyel5NiYqi3ph5DLYErxUpQA59piUNod92rYNHFVumrNSDC1bjSSCtx5WM7qEJypR8gg4yXDRFjujKytDoUnMImJSjU6XeR6xxqVQlSeWhA0i/K4gKkdLLZNUKr4E7N1SRbKsCZmJQ9Xxxk7pJSO8gYjPbRekLs6sSuS9JrU1OOuTMm3Oy70oz1zTrLmd1SVA4Od0xdrG4l3MY2coFBnn1vzlEpsy8569x2VQtSuWpI10iE3+ltslZ0cXWkqxkAyJBPuxvFf2xWpRrttq2JpFQM/ccuzMSJQxlAS4SE75zodDmK4tPGBldyRkoSkAJGABoBHjOycpPS6pedlWJplYwpt5sLSfKDpGB2hXlSLEs+buiueEeASim0u9Q3vry44ltOBz8ZQjCVza3atG2XU7aNOpn/USodT1O4xvO/Tc7mU57oxwxuMlKbMNm0nOInZTZ9akvMoO8h1qkMJUk9oIRoY2pCEtoShtISkaAJGAIg2X6WOyJx8MrnKs0ScHMgpRB8icmJSm73tpGzyZv2UqCKhQZeTcnDMSh395tAJVgdowRjjkYiuMl3QTXkZ6ZZl5phUvNsNPtKxvNuoCknBzqDpFl6g28eNCpf4oj4og9fS32SpJStdaQoclSRB9+JM2S7R7d2nW9MV22VzKpOXmlSqy+1uK3wlKjp2YWIu1ruMmxqt63SP1hpX4m38UeTtt28tlLLlCpi2kqKkoMo2UgnAJAxxOB6IyqYDEzgPBbU2nyNNYLFPkpaUaKiotsNJbSVduABrpFzB5oIxyC2n5GTn2upnZSXmmgQrceaStORwOCOMedOpNMpynFU+nScmXMb5YYS2VY4Z3QMxemFnBjIjLOepdKn3Q5P0uSm1pTupW/LpWQOOASOEe8oxLykuiWlWGpdhHrW2kBCU+QDQRXnWAnBgMsSsnQx4TUpLzLKmJlhp9pYwpDiApKvKDoY9xxxBnWBizTU7K9mKX0vo2dWil1J3goUaXyD2+t4xtktLS8u0lmXZbZbTolCEhKR5ANBHrBFyyYGk7vA4jGy9BoMvMImJehUtl5tW8hxEm2lST2ggZBjI6QZiDI1HPGMbP0Kizz/hE9SJCad3QnrH5ZC1YHAZIJxGRzpADDIPGSlZaSlkSspLsy7CNENNNhCU+QDQR684PPB54gDnBzhQQAQQQx2xSighwRCZDug9MGdYOfGKMhChmFAoQQQQGQgPCCGYAfIxTFXKKYhAhwoIpQEEEMQAoPNDgzAB5oQx2QQQAQQQQAQQQQAQ4UOIQPJB5oIUAPPkgzCgijAycwCFBApVBCggyjEOFDyIFQRWDpFENJ1gXBXBBAYxGAJhg8oUEAaXtys1u/dl9Yt3dSZtbXXyKiPWTDfjNkecYPaCRziBdi22dNF6K9YmZx0irWvmnyjbisLX1v6mGOW6VFB0/ciTzjq/jxMcj7UOjZctb2xTr9D6hizq1ONTdQUmZCFNEk9aA37I5Kyk8i4Y2waxhmE0+6Nv6MdkuWp0dapV59KvVO4ZSYn3lODxw0WiGknOuSkb571mNN6KduzV49FG8rVlJlMtMVKbeYadVndSoy7OM45cj3R1JWqYXbWnqZItJRvSLkvLtDRI+llKU9w4RCewDZdtFsvYZcdqqnJGhXJOza3JCbSvwhDQLTSN/TGFeKrHHBwdeEHJYZFF5I52e3jtI2H2t8zVz7FXqlSpeYccXUZbiQtZUpSnEIWheMnBUU6BIOMRIV73RZV59EO6p6x5Fqm05lhbbsgmXQyZV0uJcWlSEeKCd/eyNDvZzFsk9LiVp5obsjZ9S32+qNTKk5wRgqVqkE+RvHcY2vYvsNl7T2M1qx7inUTj1wBZn/AAfIQyFNJbShsnU7oSDvHGTyEWTS95vksYvODL9EtpLfR8tQDH6nc+FXEcdFZIHSF2vlPDwz3fCpiLG2rS6TGzClrtCzjbtdogdWqVm3sBTG+cqISpSSgFRKt36Zgk8tI3DYvswuvZlZ10Vd2Zlq3fNcBeUQ6UtBzxilJcUPG+mOLWpe6PXYA0hLCy89yry47Ef3lUrd2pdK92nXFVJBq0rVknZVfhUy22069wcAKjqouKA7vB/TluhddDlDq1y7IalUGpx6lzLk3TphpwKbfZKgHCgpJGCVJcxk460j2Jjz2P8ARboYtdb21SSNTuB6aW4epnnNxtGmMlJG+pR3lEnXxscouKxsEqVj7V7WvDZDIMtyUmVIqkjMTyhvoJwrcKs53kKIxnAKEHtiuUXHaY4ecluwtSv7IG530ZX/AKdMdRpSSB5RHNe0fZttcb6Q0ztJ2eylCWPAm5ZldSfO6fpe6vKBr5NRG+bLXekCq7mU7RJa0UUHql9Yqm7/AF3WY8TieGeMYWYaTTM4x55Ix6DLANy7SUuJCkqqABBGh+nPiNs6Tt+ptxqU2eWFR5WdvSugNtNy7CS5KtKyN8DGAtWDjewEgKWdE6+3R22b3vs/mL8nKlK09MxVXlP0wImd9K1bzqkheg3dVpiNbR2bdI+2bxnrzakbSqlxz6Nx+fqkyXlDON7qwkJCM4SMDQBIAwIy91zbyTDSxjuT50f9ltO2V2SimNluYq0zh2pTYH6Y5jAQnPBCRoB5SdSYg7oBLA2Z3pr+7I/9MIlnZRM7eHrlfTtMlrXao3giyyaZvdZ1+8jdByT4u7v+fEat0Utll27ObNuWk3KxJpmag4Fy/g7/AFiSA1uanAxqIxTfOfMrXocxbImruti0kbX7RWp71AnkSVRl9048HUyhalLwclokhKtPFO6rgkxLYvKkX90wtm900ZSvB5mmNJdaUfHl3kond9pf2Scjygg8CIlHojbLrisCw67Qr0kZLen50OBpDoeQtrqUIIVpjXdOkana3R0rdldIai3Fbhln7PlJpUwnrXyJiWSppxHVYOd8JKhhWc40OoydnUi857mKrcexjGqNTdonTkrlMvKXZqFPo8kvwOSmU7zTgbQwUoKTooZfcWRjBI14RMu3+Z2XWtaMnWdoFrStRpzM62iXCKel1TbuCtPkHiEHkRocgxq+3rYvc1cveV2kbM6+3Rrol20odbc8VD+7oFheFAK3SUlKkqSoAZxjJ0W97G6Se1uks2verFrUiktvh5b7R8ZSwkpCsJUsqxvE48X+iMHiWHky5XGDqqQnW5unS04ykhp9pDqARghKgCPfjk/aNKSt/dNymWtdWXqNIyCCzJuKPVu4bU6U47FqIz9UEAHIGI6vpEl4BSJOQLnWmWYQzv7uN7dSBnHLOIhjpC7Eahedep182TWBRbwpiUpbdUopbfSkkoyRncUkqI3sEFKilQIxjXW1FmU02iSLm2f2Xc9JapNbtikzkkypKmmlSyQGynhu4GU9mnIkcDHOvSEkZe6OldYWz2tDdtpEq06JRJ3G1lZfKuHI9ShHk3gOMZeco/SyutluhVGp0C2JULT11TkVBLqgOzBUTrg4ARnHHGQd4297GJraFRaLUJGuplLyoiE+D1Pqy0JjGCQdw5bO+AtKhndOeRMZxxF8sjWY8I3+4bBs6s2i7bM9b9MTSup6tDKJZCEsADxVN4A3CniCMYxHKPR/qs9N9EDapTZh5bsrJykyqXz61HWSoUsJ7AVZVjtUe2N0qVO6WlxUpdp1By2qbKPI6mZqzLgS643wVhSSTkjOd1CD2FMb9R9jbdpdHe4NntvutztVqkhMJemnU9UmYmXG90HTO4gAJSBrgAcTnNTUVhvIxl5SOc+jVc9T2XV+3bgrEwUWXe3XSbrpyG5WaZeU2lSzwB8XjplKzn9LzGD6Rlcqe09dx7S2HVotWjzaKDSUqyQ+VJWpbidcDOAonGoKBpu4jo+zthr9R6M0vszvPwaUqjT8xMMTTH08SjynnFtuJ9bvaLwRkZBUOcW+2XYhUH+jpSdmdhMMTL8lONPOOzDgZ64hLnWOqOvjKUrOO/ujLqRcs+Zh02o4NO6dKFu7GLEQgbylTCQB2nwNUee2rbTsbuHZBPW5S2m6nWZuUSzJNimqbLL+AEuhakjBSddNTjAzG99KHZbd9/7NLWodtsSi5+nOpXMB6Y6tKR4OWzg4OTkxLNvWVatKbl35W16JKTqG0hbrEi0he9gZ8YJzGClFL6mTjJs5J2r0Ws0DoMWlIV1h5ibFV67qHgQtltzwlbaFA6pISpI3eXDlHXdk7o2d0UkDApTPwQjDbcNn8ttM2eT1rTE0ZNxxSHpWZ3N/qXkHKVFPNJ1SR2KOIgiRoHSupdsJsGSXbrlNQwZZqqqfBebZxgALOuQNAS2T3k6wzvjgbXFl5/Y8WGZjZpcjb7LbrZqjWUrSFA/2s1yMWu2RmVY6cOz5luWZQyadLZQlsBJyue4jh2RNOwHZrL7LLAbt9uYTOTjzypmdmEo3ErdICcJHEJSlKUjPZnnGjbTdmV217pPWjf1PYlFUSmSrLU0tb+64lSFzBOE41GHk8+2EZJSbK4vbg2vpMNS7GwC9PBpdloKpbgPVoCc+iIB2GbQ9otC2XUilULYbNXTTmC8Gaoh8gP5eWVadUrG6SU8fYx05trtmpXZsmuK26Olkz9Qk1MsB1e4jeOOJ5CIR2f210obGtOTtegSFh+p0mXC14S6445461LVlQIB1UeXCLFrY+SSjmSNw23T85VeiZW6lU6Au356ap6HJinL9dLrLicpOgz5cCI32Sbatjlv7Fqbat0sifqkvJuNTUkaWp0O5UohJUU7pBBGpONYlK4rd2r3r0frity8JWgIuqdc6uWTIuqRLqaCm1AqJyQdF+5GMpOwSm1Lo9ytl3NSqVK3EiWV/dCXaStbT4UooX1gAUoYIBB4gkGEZRUcP1JKL3cGL6AtDrtK2c1ecq0pMystUJ9DkoH0lJdCWUJU6Add0kYB57uY6BuOryNAoM/W6m8lmTkZdcw+tRwEoSCT70R30cKXtDt6w2bb2gsyy5mnHqpObYmQ71rHsUq0B3k8M8xjOuYt+lJbV83rs6+ZWyWZVS56YQZ5yYmOqAZQd7cGhJ3lBOR2AjnGuT3TyzOOVHBy9SrcpW0/Z1tDv25a1SJS8KpO+EUqVmZ1pDqENYUppIUoEBST1IJ49WlWO3qzo1XqNoGyCmVJ9wLqUqkyNQSfXB1sAbxHLfSUr/nRgqT0X9ksvKS4nqJMTs2htIeeXPPYcWBqrd3sDJzpFlsI2Z3nsw2p3NLS7cq/YdUJXKHwnLzK04LZKSNcJKmyckndQeRztnKElwzXGMk+UQh0PtqOz/Z3aFWlL1mzLzE9NtvSwEkt/eQGkpOqUnGoOkbZ0ewxdnSrrd9WTQ36VZ7co80451JaaecWGxgJwAFLWN8oHDdycFUbr0XdiE5adnVyj7R6BRJ5ycmE9TkImPpXVBCgFFOU6g6DtjIdHzZ1feyy7q3brvg9TsabdU/IzRmR4Qy5jQqbI5pASrB1UkKxqQEpxw8BQllZI06G0hIX9tIvK/LvlmZ6utvpcal5pO+ZRTil5Vuq5pCQ2kkZSEEDGTHT1Qs61J245K45m36a7V5BKkys2qXT1jQPHBx6OzJxxiDr72KbQLX2lz20PYvWJKXeqKiuepM34rS1E5XjQhSVK8bdOCFFRChnEXllUTpI1++6TXL0rVItqkU9RLtPkUhwTY4FKkBSuIOiivxcAhOYxn73KZkljgjS9bluG1OmdW6va1sPXPUxJdUintKUFKSplveXlKVHxd0cucYPpS7Qtod4WRIyV47MZu0pNicU8zNPOOKDrnUuJ6vxkJHAk8eUTpSNml1S3S2ndo7svLCgPSS2EOB8FzeLSE6oxwyDGQ6XOze6Npti0uj2siTXNS9RMw6Jl/qk7nUuI0ODk5WNIu+O5GOJYwR907cK2J2Wf9pH/AKJyOmJGQkn6JKOPSku654Igby2wo43BzMQ70otl92bQdmVt0G22ZNyep7wXMJfmOrSB4Mts4ODk5UIm2QbcYpMvLOAdY3LpQoZ0yEgRg3wjZjnk5b/seEnKTNjXKqZlWXimfZwXGwrA6hHbFr00J2Ypu2bZrN0+mmoTEqkuS8ijQzC0zLJS0MA43iAngePCJC6H+zS69mdsVunXSzJtvTc226z4O/1oKUtBBycDByIxnSb2Z7QLw2g2hc9kS1MddoIU7mdf3E9aHUOIyAMqHia8IzUlvyYSi9uC6sfaltJrV202l1rYBO0SnzL4Q/UHHFKTLpwTvEFkdnaI0TajTpK/em1S7VuhanaNJyLYZlFrIbdw2p0pxn2asZxxCADkCNu67pdfwDZ6fO58qM30hdis9e1ap17WVWBRbvpiEoadUopQ+lJJQCoZ3FpKjhWCCFFKgRjEjKKZWm0SHcezuybiozVHrVr0mbkGSkssGWSkNFPDcwAU6aaY0JHAxmpil0tMmpKadJhLbPVoAYT4qQNEjTQDkI50n6b0tbolBb87N27bsuopD1Vk3Ah4gcSkpKj36JQT2iOjaRKz0tQ5aTqU+moTyJdLb811QaD7gTgr3BkJydcRi+H3KuxzH/Y85KWmrBuQzEsy8RUWcFxsKwPB0dsVdIeUA6WmzHACUJaYAAGAMTDn9Ub50P8AZpdOzK1K1Tbqak25ibnG3WfBn+tSUpaSjU4GDlMX3ST2SVHaG3R69a9TZptzURwrlHXSUpcTkKA3hncUlaUqCsKxgjGsZxmlPnsYyg3Hgp6Y7G70d7hxrh+RP/7jMRTtV06BlmgjXdpnvxk7tszpIbUaczaV4vW9Q6KHULmppjCi8UHKVbiVErwcKCfpYyAeWI3rb9szqVd2ESez+ypdlS5F2UTLIfd6sBtntV249+Mk1HHPmRrOeCN29uexlvYXLWvVZb1XqTVGRLOyJpiiC8G8arUndGFa72eWYq2T0auUboO3sK2zMS5nJOoTMqy+goWloshO9unUBSkqUO3OecbddmwOl3PsMp1uuUWkUy7JOQaKJ1hhCT4QlGFIW4kAqQrUHyg8QIz9It3aRWujjW7Mu+VkRc7lMfp8u+3NBbc0C3utrWceKrXCtOWRxwDcV2CT4IN2A7QtoFvbM5OkW7sTmLtp7MxMKRU23SA4pTqlKTjq1Y3SSnjyjqvZfUqrW7JkatXLWNrVKZLhfphOSzhakpJO6nJKQlXDniIB2cWn0ndn1qtW1bsjY/gDTzjyfCnluObziipXjDdGMnTSJx2Qu7S3KFNnaezRWqmJr+1hS89WWdxPrsk+Nvb3mxGFj54MorC5NzxiCDSCNbKHkggggAMeee6KicGKNe6MkMDHmhKORBwhHMAwMGYIUDFjgJ04QQQMQMHmEHnhRAOCEcwRcDA4UEEChBDgiAIIIUCD80HmEIwRQEHOCCBQggggBwQQucQgQ4UPlFKMdkUnjFXKFABB7kEEQgQQocALlAeEBheSKVDggh4gBQQ4OXCADEKHBEIEKAwRShBB6IOUAHKCDlBABBBiDzQAQxxhQQBVCBhZ7IcUqHAOOdYSTmKvdiGZUngOMVRQknMViIyBBBDiAQh8swjDBgMhmDMEEC5FDgxBiBchnhxhkAnhAIBpAmQCR2CHgDlDhQJkYURAp0JGScCEY8J2WYnJR2VmWkOsupKHELGUqSdCDDBlk9evQeCoe8Drk4jjPpB7Gbss1x647Pq9x1K3VEKelUT8w5MSGefryXGu/wBcnOuRki/6PfSFmaSmWt3aBOKm6Vu4l60tZU4wNN1L2njoxn6ZnI0yDqob1p8x3R5NLvxLEuDr0FJ0xHoECMNWaPS7mpLZTMqKFp35eblXtQDwKVA4UD2agxo7FWufZ/MplK227VaMpWG5lOSUeQnOPtVHyGNKju7Gxy29+xKQGIeRFjRavTqzJJnKbNNzDJ0JSdUnsI4g9xi9jBozTXkOFAMwQKPMEEEAHOCCCADHdBiDMUurS2grWoJSBkk8oDJVwhxgWpiaq08ky63GZNlWSsaFw9kZ2DWCKWRwj3Rhq+463UqYEOKSlT2FAHAPDjGZEMcZKnllOdYMDsjDOLcF4NNdYvq/BSd3e0zk64jN4itYCeSkAcIYxFWIwjrrovFpoOL6sypO7vHGcnlBLIbwZuCCMLITCvmhn2VuqxhJQgq04a4ETGSOWDM+WDTuxCzGDefm6TPqXMLcfkn1euOpbJglkN4M7gcoWIG1JWgLQoKSdQRzhwKHKCCCACCCFADhYEGYDwgiZFgd0PMLEWlXqUjSpJc5UJpuXZTxUs8T2Acz3CMiZ8y6UsCKesSdMxFVRq1z7QJpdPtxDlMo6Tuuzi9CvykfkpOe0jhG521b9OtWnL/tl11e7vPzc07kkDjkk4SnuGkZuCS+pqVjb47GygAjIzAQkRyTt+6Sq3w/bWzic3JfG7NVxBHjDmiXzpjtc+9+qGL2AbJrwvsM16563cdLttKsttqqEwiYnwPqcrBQ39mdVctPGjPoYjuk8Dr5ltisnZBGmRwg4R5SMrLSMizJSbKWZdlAQ2hPBKRwEep740o2tihwoIGLY8wiodhhGFAoEjvhaY4QYhgRSi0zDHuQ8QeWGSZF5hChnjCEQmQggggAGkI8DD5RQo40zrFSBSde+HiAQExSlJ11hnWEOHODPlgYN8gYRhk90KBAzBBBAMIPTBBABBD8sAEQCgh404GDECZCFD0zCgAgghxSigghwAoIeNYPNAgoIcHmgAhc4IcCh5YIUEEQqHCEYfdCgAMKCCAHCghxAEAg80EAKH54MwQAQGCFFGBwQvPDECh7kKCH5oAIXdDzrwhQAQQCDzQGA88BMGYMwLgIIXPjD5wACHCh8IABpFXKKTDBgVPIxxzFaT3xR3wZgXB6Z74IpBh50iYLgcEEEQgxx7ocUwwTnHKAHiDzwHhB5hABCgggXAwYcUHyxUDFGBwYghxCCKQRgjI4axzttz6OcpWFP3Ds+al6fUlEuTFM9ZLzJPEoPBtedfqVEnOCcx0VBmMoWSg8xMZwjNYkcH7Kdrt47Jam7Rp2Tm5qmsubs1RJ3LTsurmWioZbONd0+IrThnMdi2DflnbSaCuZoU6xOt43ZqTeSA6yT7Fxs6j3jyJjE7XdktqbSZHFWljK1RtBTLVSWAD7Q5JJ4LRk53VZHkMca3zY20bYrc7VWRMTUqlB3ZSu04EMrBI8RzOQjJx4jmQdMb2NOpqF/K4kc66lPD5idf12xqtRp9VYsadXLuD18kpWUrHYCdCPsVeYiL21tpUrMTHqbckuaNUEndV1oKW1Hyn1p7jp3mIs2PdJyk1QNUraG2xRZ3ACamgnwR444rB1ZPHiSnv5ROtetugXXINuTTTT4UnLM0yobwB5pUOI7tRGqWY+7YjKMc+9WzPtqSoApOQRkGKhEWCmXrYhKqU8quUhOvUKSSpA+1GSPKnI+xjZ7Yv+hVopYdd9T5wnHUTCgMnsSrgfJoe6NTg+65Rvjau0uGXEmxMVtT8y7OusoSspbbQcbvliqnVl2XS5LTTT00tpZSHG05yO+Lx+jZmFvSc47K9bqtKdQfdi9p0kzIS/VNZOTlSjxUYxbRVF5LA19sfvCc/Bwvmgb/gE7+DjM+aFEyvQyw/Uw/q+3/AJ38HHgszVde6otuyskg5UVDClnsjYIIZJtb7s82GW2G0tMoCEJGABHpBAIhkkYO4v1zpX8f8AFGcEYK4nWRVKcC6gFDu8vJ9aNNT2RnUkEZBBB5iK+yJHuzBOH9GrX3IffMZ6NfX+zhr7k/pMbBFl5CHmEYB4/o4Z+5D75jPxrz5/R2yP9jPvmERPyNhjF1ml+FYmJZQZm0aocHPuMZSFGK4Mmk1gxVHqSphRlZpBam29FIPsu8Rk3G0OtqbcSFoUMEHnFhWKaJtIdYV1U03qhwaeYxTRKguZDkvMoLc0z69JHHviteaME8cMtQZmiOlAbcmZJRyndGVIPZHp6vt/wCd/BxmIIZXmXDXZmI9X2/4DOfg4qFcQf3jOfg4ysPOIZXoMP1MBUao7MNty8qh6VW6sJLi04wO6LepSs1REtTsvOvOjfCXG1nIV/wB4jP1CUZnZcsu545SocUntizapBLqFzc47MpbOUoUMDz6mKmYyg2ZFJOIS3AkZJ8sazdd90GhBTJf8NnBp1EuoEg9ijwHv90aa7T77v45nnFW/RlfuQSQtweTRSv52B3GM4wzy+EYTsxxHlmcufaZTZF/1OojZrFSUd1KGMqQD2ZGd49yfSItaRZdXuGbRV73nFq5tyKFYCR2Eg4SO4a9pjYbZtO37UlSuTYQhwJ+mzTxBcI71H1o7hgRC+2DpPUSihdLsBMrcFQOQqfK8yTGnFJH6cc8kkJ4+NyOcVueK0a845sf6E03rd9o7ObcTO1udlqZJoG5Ly7YG+6oAncbbGqjgHQeeOMtsm2K7Nqk2KLT5Wcp1GfWW2aPJ5emJ06463cGVnA/S05SNclWhGLtK19pm3G51z635moKB3Zisz4KZaXGcFCN0AZ0/S2xy1xxjr7Y5sdtTZrLB6SZ9UK2tBQ/VZhA61QOCUoHBtGg8VPHAySdY2pV0cvmRjmdzwuERPsH6MzEkpi49pLLM3M4C2KIQFssnkXzwcV9iPFH2WhHTyUpQkJSAABgAQ8+mETodBHPOcpvLN8YKCwh55ZhcoDwg9+MDIMws6QswRS4DnBBD0iAIIPNB5oEDMIk9ukIkk6YggQICYMwcoFCCCETACUeyKTxzBBGQAwjkwEwZwIEYuXGEYZ4wiYGIQQocChBBBAg8QcoPNB6IEDzw4XoheSIMDJHbBz4woIoCCCCBQhwQRCAIPPB5oPNABzgg80KAGYUOFFKEOCCACDWCFAFR4cIWsPlFMAEPWFDiAIIXGHy5RQKDMEB4QKEGuIINIEDEEA88EAEEA4wQAQ88oXvwQA4UEEALvEPXshGDlzgUBmCD0w8awAucOCCACDlBBr2QAc4Zik8Yq5QHmMaiDzRSOPCKgcxTYEVg5imCIQ9IIQgOYmCD5QHEELSIB5xDhadkA8U84AfLlBBiAxSh3wQQ8d8QADDB74pgyQYDBVAeyEDD0zAgo8J+TlJ+Tdk56VZmpZ5JQ6y8gLQtJ4gpOhHli4Ihd0XJe5zHtc6L0u+tdV2bPsyS8Ero8yo9Ss/6pwklvn4pBTwxu84dsvaBtJ2PVk0haZ6QbaJ6yiVVpXUrAIyW8+tH2TZKTnOsd/8ACMDetnWxelK9Tbno0pU5cHeb61HjtKxjeQoeMhWp1BB1johqHjbNZRzzoWd0HhkfbLekPZF4JYkqrMN21WHCEeDTrw6p1Z4Bp44SrJ4A7qu6N/uWzrfuBJdmJVLcwoaTDGErPl5K8+Y5h2pdFmsyImJ2w59NYkyCfUueIQ+Br4qHT4qxyAUEntUYjyz9qu1LZbVBSH359LDOQujVtleAAeKCrx0jkCklPcdIy6MZe9U/0MXbJLFqOsHaRtAtHx6JP+rUgn97rTlQHcknI/mq80ZKg7U6VMOeCV2Vfo82nRQcBUgeXQKT5x540XZ10n7IrrSJe6GnbXnseMp9XWypPaHgBgfbhPniX3pC17uprU0W6fVpRxIUzMNKS4CDwKXEn3QY1SWOLEZRWea5GWkJ2UnmEvyc0zMNK4LaWFJPnEXMRzObM1SbxmbYrk3TXeO4pRKT/OBB9OY8jVdo1vpxUaWmtsJ4uMjKsfzBn/hjDYn8LNislH4kSVBGh03ajQnldVUZecpz3skuN74HnTr6QI2ql1+iVROafVZOZ+xQ8CoeUcRGDhJd0bFZGXZmSgJIQd0DONBC0gzEwZZNaoMvT5qTeeqBSuYKz1nWLwU/99sXVoOqXKPoC1LZbeKWlHmI956hU+cfLzjakrPrtxWAryxkJWWalmUssoShCdAkCK3wa4p5MIs5vtof7H/SY2Axrrml/tDJ/UX9JjYT54svIsfMYjXnz+j1gf7EffMbAI15/XaAx9xH3zCPmWXkbFmAQAQd0Y4MsjjB079lM/8Axaf6IzQIgSlsLKglIUeJxqYdidxnSCLKp1elU1vfqFSlJUf615KSfJk6xqdV2nW9Kq6uRTNVF46JSy3ug+dWPczFjFvsiSnGPdm8mLedm5aTYU/NzDLDSdSt1YSkecxHYre0S4AfUqiJpDCuD0wMKx/PHvJiuV2aPz7wmbqr81UXM56ttRCR/OP9AEZqCXxM1uxv4UXFe2pUeUX4NR5d6sTStEJZBCD58EnzAxj26ftCvAb1Smhb9PV+4oBCyO9IO8f5xHkjcpKlW3a8k4+zLyVNYQnecmHFBOAOJUtRz6TEUbQuk1YVvIWxbq3LqnuCRIrCZYHX1z50xkewCj3RnFZ4gjBprmyRKVs2Xb9vhLjEqH5pI/VD/jLHk5J82I03apt4sex0vybc2mu1ls7pp8g6lRQrsdc9a33g5VjgDHK957ZNqO0uo+pEi7Oy7Dw8SkUJpxS1jI1UpI6xYz9qntHON42X9FyvVFMvOXvPIoMiMH1OlN1yZUNPFUseI3zzjePYRy29GMfetf6GPWcvdqRoV/7StpG12riiMpm3Jd8ANUCkIUpChnBU4QN5wa4JXhAGMgcYlfZF0WUpW1VdpUwh0aFNHlHDuDX91dGCr7VOBxyVR0PY1j2rY9N8AtejS1PbVq64kbzrx4ZWs5Us+UxsMYTv4xBYRlCjnM3llrSadT6TTmKdS5KXkZKXQEMsS7YbbbSBoEpGgEXROsHDugxHObgEEA88I89IAD26QideUGkAEChrAO2DEPEAEEGkKBAhEk6coDAIAOfCFATDzABwMB4QCEYACcCKIOesEZAOUI8IMxSTk84FwPnCJ9MB7YWBAwA5g80EOAFDgg7IAIPPBBABBCg9yAGfJC7sQemDjAD9EAgMHKBAghwoEHCgggUcKCCAHCg0ggBpGTiF3R6tJI1MUupwd7kYhcFEOFDGIpiLyQeWCA90EUq5QoZ4QogFDhQRSBBBBAoQcoIPLArHBBzggQPNBBAOMCCh8oIIAUEEEChBDggBY7oIcKACCCCAHCgggUIIMQQADMOFDB5ZgRgIBBD5QGRjyQRSDrFWdIGYwcRVFEECnoOyCKM5iocNYjRBwHiIIcQZAaaYMMQuEIHHbAFUHKFnPDMHlgUIIIIAPJDBPlhAQ4AY17ocUwZgQq7oUEGYAOXCMFeVn2veNP8AALnocjVWAd5AmGgVNnhvIV65J1OoIOsZ3SFDLRcZOYL86KEuXFzViXEuUTjPqfUwXUE40CHgd5PfvBfHiIhqaoW17ZBUFuMy9et9OSszdPy9JOcyokBTZ4fuiQdOEfQYRSsJcSULSFJIwQRkGOmOqmliXKNEtPFvMeGcg2V0r7kk2mm7noUjXGfZTUk74O6Ry8U5Qo+dI8kTRanSJ2WV1tPhFwJoTxxlqrJ8HCSeW+SUHzKIi/vXYdsyup5yanLZl5KdcO8uap5Ms4o9qtzAV/OBiFbt6JdSaWt21LvZmmseLLVSX3HM9nWt+KR/MHnit0WfRmP8aH1R0+5LW9ccml5TVNqku4N5Didx1JHaFDPpEa3VNl1szZK5ZMzIr5Fl3eA8ysxxjUNmW2TZ3MLmJOh3BJoSveMzQXlvNKV9UUsnePlUgRe0Pb9tetqaErPXCZ5WAfBa1IJ3wO3QNuekmKqJf0SyYu6L+OJ1ebFvCmnNDvV/cHBt9Kse+oe5Hq2varIYDrMhUkjmndyfdT70QvQelpUUFKa7ZTDqcauSU+Uq+8WjH/FG9UbpTbNptsGoS1epKycbr8l1vusqXpElXau8ciLqfaWDdU3ldkp+uFlzKgOJaC8e4lQipO01lvSct+osHyA+/iLSS28bJJtKVG+aXKlXBM0pTJHl3gIz1O2k7OKqvq5G+7Wm1/UNVVhavRvZjQ1zzE3rOMqRi7cueTuDaC0uUZfaAklJIdAByD3E9sSBGOlahQ3D1krPU5wngpt1B90GLkzkseEywf54jGXL4RlH3Vyz3JAiP7uuaUt+/Zd+baedR4DjdaAJyVKxxI7I3jwqV5zLP4QR4PzlHR9MmZyQSR7JxxA9+EXh8oksyXDNQ+edKuD+1aDU3j2bo/ozFCr1uia/W+y5vXgp0OY91KR7sZmp7Qdn1I0qF72xInseqjCCfMVRgZ3bpsllQr9HtGmCPYyz3XHzbmYzS9Ik5/qkUPTG1aeyGJKQpyTzXu5Huq96PH5ir4qagazeq2kH1zcuFH3ige4Y12s9KPZhJtrMiqtVVxP7nLyCkZ8indxPuxoVe6W8ws7tv2MEp/ylRqGFfeNpUP8AijdGFr7RwaJdJd5E50zZhbsuoOTzs3UHeJU67ug+XdwfdjZpaQt+gS6nmZSn05pIyp0hKMDtKj/THDtw9Iba3cMyZKn1pimKVkiXpEilTxT5V76j5UgRjJGwNs20iYDs3RbnqLal5MxW3FsspONFAPEZ8qEmK6Jf1ywVXRXwRydb3T0g9lVDbV1VysVp0ZAapI8KyezfT4g8pUBEJ3v0rrgnEOtWpb8pRmfYzU+517uOeUJwhJ/nK88e1pdE2uTCmnLru2VkGcfTJemS/WuZ7A65hI+8MTXZmwnZja7jcwxbbFRnWzvJmakTMrSrtSF+Kk+QCJ/Ar+rK+vZ9EcgM0va9thnUFxq4bkbUQoTE2CzIoGchQJCWdM+wBPYImOwOiakONzl93EXUYBNPpiSgZ5hT58Yj7VKfLyjqdtKEICG0pQkDRKRgCHk9sYy1MmsR4LHTxTzLk16yrKtSy5AyVr0KSpbSjlwstALcPatZ8ZR7yTGweaDMG9Gjlm9cBBCz26QzEAiYMwc4IpRQY8sOCIMhyg5wQQIEHmMKAnHbABCzAYDAoQQs6wzw0gQMcoMQeeKVHlBAY0GIpJyeGIRMEZAIR4QEwoAIIIUDFvIQQQ4EyHmhQDywQAQeaCCBQggggAgg8sOAyKCCCBMj9yFBB3QAzCgggAgghwAoeINYIhAAzpHqlAGp1jyENKiDx0gVM94WOUCSFJyIS1bo74hmUKbHEHTvjzMMqJOphCMjFhBBBAjGeEIwzwggBQQQQAQQQceMChBBBADgzzhQQGA80EEGvZAmAggEEBgfKFB54IAfCDzQjB3QGA1ggggUIIXPhDgAghQ4AIIIIAIIBBAgZg8sGsLECj0gOYOUECp4KgeyHrFI056xVmBkHCKgYpggQqyYY4RSD2wAnlBouCuDyRTkw0nSJjBMATjhDyO2A6wCICqCEO8wZEChBmCCADnBBBABAIIIpQEVCKR3QDywBVAPNBAO2IQIY48IR7IUAVaRja3QKFXJZctWaNTqkwsYU3NyyHUq8oUDGRg5Q7DBFtb6PuySqA4tNmnEnOac+5Lf8KFBPuRpVZ6JtnzKlLpVzV6nH2LauqfbHl3k7x++joeCNiunHszB1Ql3RyTO9Ea4G1HwG/qXMDsepTjR9KXVe9GBqnRV2ht5ErP25PfbPuN++gx2oIMxsWqsXma3pq35HB0x0XNpzWpoVuvfxU8kk/fNiLcdHHau1o3astgfUTrIHviO+YMxl4uwxlpYP1OBh0c9q7hwq1mMfZzzJ/5jHu10Xtp7uCKBQGif8rOpHvIMd5DIhaw8XZ9AtLBHFFL6LG0dfizMxbUkO1Eytz3mxGflOiPcrqv7dvqkSyf9VTXHj7riI651hRi9VY/MyWlrT7HOVH6JFrMqQuq3dXJ4j1yGW2mG1f8ACpQ++jdqL0dNklM1XbSqkrj/AHQm3Xx96VbvuRLAgjXK6x92bFVCPZGKt+2bct6XTLUGg0ulsp1SiUlUNJB8iQIypOvxwQsxh3M8D8wg1hZJ4Qa5iYGABEGYNe2ETF4KEB4wc4PLDICH5YUGYhA1hwswQAZg80EEUDEEKET2RCYHnlCEELyGAHCwYNRCJMUqHjug4A5hEws6QBUoxRkwEkwcYoAwvPAYWvOADOe2DTEGkKBg3kIPNAIIDAQGCDWACCCCACCCCADnBBBABBBAYAIPRBCzpAD4QQQd8AA4QQDSCAHmCFDgQIIUECYHChwoFK2jhWO2KVElWYUEC5DnBBAYEAQGAQzwgGHKFFRx2wtO2BA88KHkdsGR2wKLnBBpnjAe3MBkIOUHng4c4FyAgg07YAR2wGQgg0gPlgMhBBp2wZHCAyEBg88EAHuQofOCAyB88EAEHngAgg04QaQGQgg5waQJkIIIIFCCA8IeIEEcQe5Bzg0gXIeSDzQ/LBAgCCEDmGBAyWV3GNfLB5oB2iGIGQQQeeAAwA9IeYp96GIAqBhxT54AYmAVQuGsGYMxMAYPbD46iKRDyAIoHBCyM6mHkRChBxgyO2DIxxgQIIMiDOsAEEAI7YM98AGYeRzEU5EPIzAoZxyh5ELI7YARAFWsKEDrxgzpnMAPJgzmETzgB1ikGDB6YMiHlMC4FpBBlOYN5EQBmH6YpOO2HnvigO2GAYpz3wE98APSFwhZEPMMgZML0wgRDJHbEIEELeHbDyIABBiAkcYMjtgUIMQiRDyMQIEGYMjthaQAZA4wHhx1gyMQucUDJ7YQMIwAwwB8YPJBkwie2GBgMwQjBnMUoZ7opMVEEQoEEIZxByhHWAEeEEB0hQMWwgg48IIECCDHfAMQAucODGsGRzMBkOcEB8sPzwGRQQ8CFpiBMhBmCAwLkIIO/MPEBkXmgxAMdsBxAZCCAY7YNM8YDIQcNINO2DSBMgIOUHLjB54AOUEGnAmA47YAINYNOR0g07YFCCAkDnD0gQUEPTthDBgAgEB8sHbBA//Z"
             style="width:340px;max-width:90%;border-radius:16px;
                    box-shadow:0 8px 32px rgba(99,102,241,0.18);">
    </div>
    <div style="font-family:'Inter',sans-serif;font-weight:900;font-size:2.2rem;
                letter-spacing:-1.2px;margin-bottom:10px;color:#4338ca;line-height:1.2;">
        5-Stage RISC Pipeline Simulator
    </div>
    <div style="height:4px;width:80px;background:linear-gradient(90deg,#6366f1,#a855f7,#8b5cf6);
                border-radius:2px;margin:0 auto 14px;"></div>
    <p style="font-family:'Inter',sans-serif;color:#9ca3af;font-size:14px;
              margin:0;letter-spacing:0.8px;">
        Visualize &nbsp;&middot;&nbsp; Analyze &nbsp;&middot;&nbsp; Compare pipeline execution cycle-by-cycle
    </p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ─────────────────────────────────────────────
# INPUT AREA
# ─────────────────────────────────────────────
left, right = st.columns([3, 2])
with left:
    st.markdown("""
    <div style="font-family:'Inter',sans-serif;font-weight:600;font-size:13px;
                color:#6366f1;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:6px;">
        📝 Instructions
    </div>""", unsafe_allow_html=True)
    default_program = "ADD $s0, $t1, $t2\nSUB $s1, $s0, $t0\nLW $t2, 0($s1)\nSW $t2, 4($s0)"
    instruction_text = st.text_area("", default_program, height=200,
                                    placeholder="Enter RISC instructions, one per line...",
                                    label_visibility="collapsed")

with right:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#f8faff 0%,#f0f4ff 100%);
                border:1px solid #e0e7ff;border-radius:14px;padding:20px 22px 6px;
                box-shadow:0 2px 8px rgba(99,102,241,0.06);">
        <div style="font-family:'Inter',sans-serif;font-weight:700;font-size:15px;
                    color:#4338ca;margin-bottom:14px;display:flex;align-items:center;gap:8px;">
            ⚙️ Settings
        </div>
    </div>""", unsafe_allow_html=True)
    enable_forwarding  = st.checkbox("Enable Data Forwarding", value=True)
    enable_hazard      = st.checkbox("Enable Hazard Detection", value=True)
    anim_speed = st.slider("Animation Speed (sec/cycle)", 0.1, 1.5, 0.4, 0.1)
    mode = st.radio("Run Mode", ["▶ Auto Run", "⏯ Step-by-step"], horizontal=True)
    st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
    run = st.button("▶  Run Simulation", use_container_width=True, type="primary")

st.divider()

# ─────────────────────────────────────────────
# MAIN LOGIC
# ─────────────────────────────────────────────
if run:
    try:
        instructions = parse_instructions(instruction_text)
        p_on  = Pipeline(instructions, forwarding_enabled=True)
        p_off = Pipeline(instructions, forwarding_enabled=False)
        tl_on  = p_on.run()
        tl_off = p_off.run()

        # สร้าง timeline แบบไม่มี hazard detection (instruction ไหลตรงไม่มี stall)
        stages = ["IF","ID","EX","MEM","WB"]
        n_instr = len(instructions)
        n_cycles = n_instr + len(stages) - 1
        tl_no_hazard = []
        raw_strs_tmp = [i.raw if hasattr(i,"raw") else str(i) for i in instructions]
        for c in range(1, n_cycles + 1):
            row = {"Cycle": c}
            for s_idx, s in enumerate(stages):
                i_idx = c - 1 - s_idx
                row[s] = raw_strs_tmp[i_idx] if 0 <= i_idx < n_instr else ""
            tl_no_hazard.append(row)

        if not tl_on:
            st.error("❌ Simulation ผลิตข้อมูลว่างเปล่า")
        else:
            st.session_state.sim_ready      = True
            st.session_state.timeline_on    = tl_on
            st.session_state.timeline_off   = tl_off
            st.session_state.tl_no_hazard   = tl_no_hazard
            st.session_state.instructions   = instructions
            st.session_state.step_cycle     = 1
            # เก็บ register state หลัง simulate เสร็จ
            st.session_state.registers      = list(p_on.registers)

    except Exception as e:
        # แสดงแค่ error message — ไม่แสดง traceback
        # แปลง error string ให้ plain text (ไม่มี monospace แปลกๆ)
        import re, html
        # escape ทุก character ที่ Streamlit/Markdown อาจตีความผิด
        err_lines = str(e).split("\n")
        err_html_lines = []
        for line in err_lines:
            clean = re.sub(r"[`]", "", line)
            err_html_lines.append(html.escape(clean))
        err_body = "<br>".join(err_html_lines)
        st.markdown(f"""
        <div style="background:#fde8e8;border:1px solid #f5c6c6;border-radius:8px;
                    padding:14px 18px;font-family:'Inter',sans-serif;font-size:14px;color:#c0392b;
                    line-height:1.7;">
            ⚠️ <strong>Simulation Error:</strong><br>{err_body}
        </div>""", unsafe_allow_html=True)
        # ล้าง simulation เก่าออกเพื่อไม่ให้ animation ค้าง
        st.session_state.sim_ready = False

# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
if st.session_state.get("sim_ready"):

    tl_on        = st.session_state.timeline_on
    tl_off       = st.session_state.timeline_off
    instructions = st.session_state.instructions
    registers    = st.session_state.get("registers", [0] * 32)

    if not enable_hazard and st.session_state.get("tl_no_hazard"):
        tl_nh_main = st.session_state.tl_no_hazard
        df_nh_main = normalize_df(pd.DataFrame(tl_nh_main))
        df_nh_main["Cycle"] = range(1, len(df_nh_main) + 1)
        timeline_main = tl_nh_main
    else:
        timeline_main = tl_on if enable_forwarding else tl_off
    timeline = timeline_main
    df_tl  = normalize_df(pd.DataFrame(timeline))
    df_on  = normalize_df(pd.DataFrame(tl_on))
    df_off = normalize_df(pd.DataFrame(tl_off))

    instr_list  = extract_instr_list(df_tl)
    # reindex Cycle ให้เริ่มจาก 1 ต่อเนื่อง หลัง filter แล้ว
    df_tl["Cycle"]  = range(1, len(df_tl)  + 1)
    df_on["Cycle"]  = range(1, len(df_on)  + 1)
    df_off["Cycle"] = range(1, len(df_off) + 1)
    max_c           = len(df_tl)
    metrics_on  = calculate_metrics(tl_on)
    metrics_off = calculate_metrics(tl_off)

    stalls_on,  details_on  = count_stalls(df_on)
    stalls_off, details_off = count_stalls(df_off)

    # วิเคราะห์ hazard จากชื่อ instruction
    raw_strs    = [i.raw if hasattr(i, "raw") else str(i) for i in instructions]
    hazard_pairs = detect_hazards(raw_strs if raw_strs[0] != instructions[0] else instr_list)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎬  Animation",
        "📊  Timeline",
        "⚖️  Comparison",
        "🗂  Registers",
        "📄  Report",
    ])

    # ── TAB 1: ANIMATION ──────────────────────────────────
    with tab1:
        st.subheader("🎬 Pipeline Animation")

        # Hazard summary box + Explanation toggle
        import html as _html
        if hazard_pairs and instr_list:
            # ── Hazard summary ──
            rows = ""
            for (i, j), label in hazard_pairs.items():
                i1 = _html.escape(instr_list[i])
                i2 = _html.escape(instr_list[j])
                rows += (
                    f"<div style='margin:4px 0;font-size:13px;'>"
                    f"▸ Instr <b>{i+1}</b> <code>{i1}</code> → "
                    f"Instr <b>{j+1}</b> <code>{i2}</code> "
                    f"<span style='background:#fff3cd;color:#856404;padding:1px 7px;"
                    f"border-radius:10px;font-size:12px;font-weight:600;'>{label}</span>"
                    f"</div>"
                )

            st.markdown(
                    f"""<div style='background:#fffbea;border:1px solid #f0c040;border-radius:8px;
                        padding:12px 16px;margin-bottom:4px;'>
                        <div style='font-weight:700;font-size:14px;margin-bottom:8px;color:#7d5a00;'>
                            ⚠️ RAW Hazards ที่ตรวจพบ</div>
                        {rows}
                    </div>""",
                    unsafe_allow_html=True
                )


        elif not hazard_pairs and instr_list:
            st.markdown(
                """<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                    padding:10px 16px;margin-bottom:12px;font-size:13px;color:#166534;'>
                    ✅ ไม่พบ RAW Hazard — instruction ชุดนี้ทำงานได้อย่างราบรื่น
                </div>""",
                unsafe_allow_html=True
            )

        if not instr_list:
            st.warning("⚠️ ไม่พบ instruction list")
            st.dataframe(df_tl, use_container_width=True)

        elif mode == "⏯ Step-by-step":
            col_prev, col_next, col_restart = st.columns([1, 1, 1])
            with col_prev:
                prev_clicked    = st.button("⬅ Prev", use_container_width=True)
            with col_next:
                next_clicked    = st.button("Next ➡", use_container_width=True)
            with col_restart:
                restart_clicked = st.button("🔄 Restart", use_container_width=True)

            if restart_clicked:
                st.session_state.step_cycle = 1
            elif prev_clicked and st.session_state.step_cycle > 1:
                st.session_state.step_cycle -= 1
            elif next_clicked and st.session_state.step_cycle < max_c:
                st.session_state.step_cycle += 1

            current = st.session_state.step_cycle
            st.markdown(
                build_animation_html(df_tl, instr_list, current, max_c, hazard_pairs),
                unsafe_allow_html=True
            )
            st.progress(current / max_c)
            st.caption(f"Cycle {current} / {max_c}")

        else:
            # Auto Run
            anim_placeholder = st.empty()
            progress_bar     = st.progress(0)
            for current in range(1, max_c + 1):
                with anim_placeholder.container():
                    st.markdown(
                        build_animation_html(df_tl, instr_list, current, max_c, hazard_pairs),
                        unsafe_allow_html=True
                    )
                progress_bar.progress(current / max_c)
                time.sleep(anim_speed)
            progress_bar.empty()
            st.success("✅ Simulation Complete!")

        # ── Comparison panel เมื่อ enable_hazard เปลี่ยน ──────
        if st.session_state.get("tl_no_hazard"):
            tl_nh = st.session_state.tl_no_hazard
            df_nh = normalize_df(pd.DataFrame(tl_nh))
            df_nh["Cycle"] = range(1, len(df_nh) + 1)
            il_nh  = extract_instr_list(df_nh)
            max_nh = len(df_nh)

            if not enable_hazard:
                # ไม่มี hazard → แสดง "with hazard" เปรียบเทียบด้านล่าง
                df_real = normalize_df(pd.DataFrame(tl_on if enable_forwarding else tl_off))
                df_real["Cycle"] = range(1, len(df_real) + 1)
                il_real = extract_instr_list(df_real)
                cyc_real = len(df_real)
                cyc_nh   = max_nh
                diff = cyc_real - cyc_nh
                sign = "+" if diff < 0 else "-"
                bc   = "#dcfce7;color:#166534" if diff >= 0 else "#fde8e8;color:#dc2626"

                st.markdown(
                    "<div style='border-top:2px dashed #6366f1;margin:20px 0 14px 0;'></div>"
                    "<div style='font-size:15px;font-weight:800;color:#4338ca;margin-bottom:8px;'>"
                    "✅ With Hazard Detection (เปรียบเทียบ)</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    build_animation_html(df_real, il_real, len(df_real), len(df_real), hazard_pairs),
                    unsafe_allow_html=True
                )
                st.markdown(f"""
                <div style='display:flex;gap:12px;margin-top:14px;flex-wrap:wrap;'>
                  <div style='background:#fef3c7;border-radius:10px;padding:10px 18px;
                              font-size:13px;font-weight:700;color:#92400e;'>
                    🚫 Without Hazard Detection: <span style='font-size:18px;'>{cyc_nh}</span> cycles
                  </div>
                  <div style='background:#e0e7ff;border-radius:10px;padding:10px 18px;
                              font-size:13px;font-weight:700;color:#3730a3;'>
                    ✅ With Hazard Detection: <span style='font-size:18px;'>{cyc_real}</span> cycles
                    <span style='background:{bc};font-size:11px;padding:2px 7px;
                                 border-radius:8px;margin-left:6px;'>
                      {sign}{abs(diff)} cycles
                    </span>
                  </div>
                </div>
                <div style='margin-top:8px;background:#fff7ed;border:1px solid #fed7aa;
                            border-radius:8px;padding:10px 14px;font-size:12.5px;color:#92400e;'>
                  ⚠️ pipeline ที่ไม่มี hazard detection จะใช้ค่า register เก่าที่ยังไม่ได้อัปเดต
                  ทำให้ผลลัพธ์ผิดพลาด แม้จะใช้ cycle น้อยกว่า
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: TIMELINE + STALL ────────────────────────────
    with tab2:
        st.subheader("📊 Timeline Table")

        import html as _html

        def is_stall_row(row, prev_row=None):
            if any(str(row.get(s, "")).strip() == "STALL" for s in STAGES if s in df_tl.columns):
                return True
            if prev_row is not None:
                id_curr = str(row.get("ID", "")).strip()
                id_prev = str(prev_row.get("ID", "")).strip()
                if id_curr and id_curr not in ("", "STALL") and id_curr == id_prev:
                    return True
            return False

        def is_stall_row_idx(df, idx):
            row  = df.iloc[idx]
            prev = df.iloc[idx - 1] if idx > 0 else None
            return is_stall_row(row, prev)

        # Filter controls
        fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
        with fcol1:
            search_val = st.text_input("🔍 ค้นหา instruction", placeholder="เช่น ADD, LW, $s0 ...",
                                       label_visibility="collapsed", key="tl_search")
        with fcol2:
            filter_stall = st.checkbox("แสดงเฉพาะแถว STALL", key="tl_stall")
        with fcol3:
            filter_cycle = st.number_input("ดู Cycle ที่", min_value=0, max_value=int(df_tl["Cycle"].max()),
                                           value=0, step=1, key="tl_cycle",
                                           help="0 = แสดงทั้งหมด")

        # Apply filters
        df_view = df_tl.fillna("").copy()
        if search_val.strip():
            mask = df_view.apply(
                lambda row: any(search_val.lower() in str(v).lower() for v in row), axis=1
            )
            df_view = df_view[mask]
        if filter_stall:
            stall_mask = [is_stall_row_idx(df_view.reset_index(drop=True), i)
                          for i in range(len(df_view))]
            df_view = df_view[stall_mask]
        if filter_cycle > 0:
            df_view = df_view[df_view["Cycle"] == filter_cycle]

        # build HTML table
        cols = list(df_view.columns)
        th_style = ("background:#4338ca;color:white;font-weight:700;font-size:13px;"
                    "padding:10px 14px;text-align:left;white-space:nowrap;")
        th_html = "".join(f'<th style="{th_style}">{c}</th>' for c in cols)
        rows_html = ""
        df_view_r = df_view.reset_index(drop=True)
        for i, (_, row) in enumerate(df_view_r.iterrows()):
            prev = df_view_r.iloc[i-1] if i > 0 else None
            stall = is_stall_row(row, prev)
            bg = "#fde8e8" if stall else "white"
            tr = ""
            for c in cols:
                val = str(row.get(c, ""))
                td = (f'<td style="padding:9px 14px;font-size:13px;border-bottom:1px solid #f0f0f0;'
                      f'background:{bg};font-family:monospace;color:#1f2937;">'
                      f'{_html.escape(val)}</td>')
                tr += td
            rows_html += f'<tr>{tr}</tr>'

        if not rows_html:
            rows_html = f'<tr><td colspan="{len(cols)}" style="text-align:center;padding:20px;color:#9ca3af;">ไม่พบข้อมูลที่ตรงกัน</td></tr>'

        table_html = f"""
        <div style="overflow-x:auto;border-radius:12px;border:1px solid #e5e7eb;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:8px;">
          <table style="width:100%;border-collapse:collapse;">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>"""
        st.markdown(table_html, unsafe_allow_html=True)
        st.caption("🔴 แถวสีแดง = cycle ที่มี STALL เกิดขึ้น")

        st.subheader("🔴 Stall Details")
        details = details_on if enable_forwarding else details_off
        if details:
            st.dataframe(pd.DataFrame(details), use_container_width=True, hide_index=True)
        else:
            st.success("✅ ไม่มี Stall เกิดขึ้น")

    # ── TAB 3: COMPARISON + BAR CHART ─────────────────────
    with tab3:
        st.subheader("⚖️ Forwarding vs No Forwarding")

        cycles_on  = metrics_on.get("cycles",  int(df_on["Cycle"].max()))
        cycles_off = metrics_off.get("cycles", int(df_off["Cycle"].max()))
        cpi_on     = round(metrics_on.get("cpi",  0), 4)
        cpi_off    = round(metrics_off.get("cpi", 0), 4)

        # ── Summary table (HTML) ──
        def badge(val, ref, invert=True):
            diff = val - ref
            if diff == 0: return ""
            worse = diff > 0 if invert else diff < 0
            color = "#ffe0e0; color:#c0392b" if worse else "#e0f7e9; color:#1a7a3a"
            sign  = "+" if diff > 0 else ""
            return f'<span style="background:{color};font-size:12px;font-weight:600;padding:2px 8px;border-radius:10px;margin-left:8px;">{sign}{round(diff,4)}</span>'

        summary_html = f"""
        <style>
        .cmp {{ width:100%;border-collapse:collapse;font-family:'Segoe UI',sans-serif;margin-bottom:20px; }}
        .cmp th {{ background:#f0f2f6;padding:12px 20px;font-size:13px;color:#555;border-bottom:2px solid #ddd; }}
        .cmp td {{ padding:16px 20px;font-size:24px;font-weight:bold;border-bottom:1px solid #eee;vertical-align:middle; }}
        .cmp .lbl {{ font-size:12px;color:#888;font-weight:normal;display:block;margin-bottom:2px; }}
        .cmp .on  {{ background:#f0fff4; }}
        .cmp .off {{ background:#fff8f8; }}
        .cmp .row-label {{ font-size:13px;color:#555;font-weight:600;font-size:14px; }}
        </style>
        <table class="cmp">
          <thead><tr>
            <th style="text-align:left;width:130px;">Metric</th>
            <th class="on" style="text-align:center;">✅ With Forwarding</th>
            <th class="off" style="text-align:center;">❌ Without Forwarding</th>
          </tr></thead>
          <tbody>
            <tr>
              <td class="row-label">Total Cycles</td>
              <td class="on" style="text-align:center;">{cycles_on}</td>
              <td class="off" style="text-align:center;">{cycles_off}{badge(cycles_off, cycles_on)}</td>
            </tr>
            <tr>
              <td class="row-label">CPI</td>
              <td class="on" style="text-align:center;">{cpi_on}</td>
              <td class="off" style="text-align:center;">{cpi_off}{badge(cpi_off, cpi_on)}</td>
            </tr>
            <tr>
              <td class="row-label">Stalls</td>
              <td class="on" style="text-align:center;">{stalls_on}</td>
              <td class="off" style="text-align:center;">{stalls_off}{badge(stalls_off, stalls_on)}</td>
            </tr>
          </tbody>
        </table>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

        # ── Bar charts ──
        chart_df = pd.DataFrame({
            "Mode": ["With Forwarding", "Without Forwarding"],
            "Total Cycles": [cycles_on, cycles_off],
            "CPI": [cpi_on, cpi_off],
            "Stalls": [stalls_on, stalls_off],
        })
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Total Cycles**")
            st.bar_chart(chart_df.set_index("Mode")["Total Cycles"], color="#4FC3F7")
        with c2:
            st.markdown("**CPI**")
            st.bar_chart(chart_df.set_index("Mode")["CPI"], color="#81C784")
        with c3:
            st.markdown("**Stalls**")
            st.bar_chart(chart_df.set_index("Mode")["Stalls"], color="#E57373")

        st.divider()

        # ── Timeline คู่กัน ──
        st.markdown("#### 📋 Timeline Detail")

        import html as _html2

        def make_timeline_html(df, stall_fn):
            cols = list(df.columns)
            th_style = ("background:#4338ca;color:white;font-weight:700;font-size:12px;"
                        "padding:8px 12px;text-align:left;white-space:nowrap;")
            th_html = "".join(f'<th style="{th_style}">{c}</th>' for c in cols)
            rows_html = ""
            df_r = df.fillna("").reset_index(drop=True)
            for i, (_, row) in enumerate(df_r.iterrows()):
                prev = df_r.iloc[i-1] if i > 0 else None
                stall = stall_fn(row, prev)
                bg = "#fde8e8" if stall else "white"
                tr = ""
                for c in cols:
                    val = str(row.get(c, ""))
                    tr += (f'<td style="padding:7px 12px;font-size:12px;'
                           f'border-bottom:1px solid #f0f0f0;background:{bg};'
                           f'font-family:monospace;color:#1f2937;">'
                           f'{_html2.escape(val)}</td>')
                rows_html += f'<tr>{tr}</tr>'
            return f"""<div style="overflow-x:auto;border-radius:10px;border:1px solid #e5e7eb;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);">
              <table style="width:100%;border-collapse:collapse;">
                <thead><tr>{th_html}</tr></thead>
                <tbody>{rows_html}</tbody>
              </table></div>"""

        def is_stall_row_gen(df_ref):
            def _check(row, prev_row=None):
                if any(str(row.get(s,"")).strip() == "STALL"
                       for s in STAGES if s in df_ref.columns):
                    return True
                if prev_row is not None:
                    id_curr = str(row.get("ID","")).strip()
                    id_prev = str(prev_row.get("ID","")).strip()
                    if id_curr and id_curr not in ("","STALL") and id_curr == id_prev:
                        return True
                return False
            return _check

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**✅ With Forwarding**")
            st.markdown(make_timeline_html(df_on, is_stall_row_gen(df_on)),
                        unsafe_allow_html=True)
        with col_b:
            st.markdown("**❌ Without Forwarding**")
            st.markdown(make_timeline_html(df_off, is_stall_row_gen(df_off)),
                        unsafe_allow_html=True)

        saved = stalls_off - stalls_on
        if saved > 0:
            pct = round(saved / max(stalls_off, 1) * 100, 1)
            st.info(f"💡 Forwarding ช่วยลด stall ได้ **{saved} ครั้ง** ({pct}%)")
        else:
            st.info("ℹ️ ไม่มีความแตกต่าง — instruction ชุดนี้ไม่มี hazard")

    # ── TAB 4: REGISTER FILE VIEWER ───────────────────────
    with tab4:
        st.subheader("🗂 Register File (หลัง Simulate)")
        st.caption("แสดงค่า register ทั้ง 32 ตัวหลังจาก pipeline ทำงานเสร็จ (With Forwarding)")

        reg_data = []
        for i, val in enumerate(registers):
            reg_data.append({
                "Index": f"${i}",
                "Name": REG_NAMES[i] if i < len(REG_NAMES) else f"$r{i}",
                "Value (Dec)": val,
                "Value (Hex)": hex(val & 0xFFFFFFFF),
                "Value (Bin)": f"{val & 0xFFFFFFFF:032b}",
            })

        df_reg = pd.DataFrame(reg_data)

        import html as _html3
        cols_reg = list(df_reg.columns)
        th_style = ("background:#4338ca;color:white;font-weight:700;font-size:13px;"
                    "padding:10px 14px;text-align:left;white-space:nowrap;")
        th_html = "".join(f'<th style="{th_style}">{c}</th>' for c in cols_reg)
        rows_html = ""
        for _, row in df_reg.iterrows():
            nonzero = row["Value (Dec)"] != 0
            bg = "#e8f5e9" if nonzero else "white"
            fw = "700" if nonzero else "400"
            tr = ""
            for c in cols_reg:
                val = str(row.get(c, ""))
                mono = "font-family:monospace;" if c.startswith("Value") else ""
                tr += (f'<td style="padding:9px 14px;font-size:13px;{mono}'
                       f'border-bottom:1px solid #f0f0f0;background:{bg};'
                       f'color:#1f2937;font-weight:{fw};">'
                       f'{_html3.escape(val)}</td>')
            rows_html += f'<tr>{tr}</tr>'

        reg_table_html = f"""
        <div style="overflow-x:auto;border-radius:12px;border:1px solid #e5e7eb;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:8px;">
          <table style="width:100%;border-collapse:collapse;">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>"""
        st.markdown(reg_table_html, unsafe_allow_html=True)
        st.caption("🟢 สีเขียว = register ที่มีค่าไม่เป็น 0 (ถูกเขียนทับระหว่าง simulation)")

    # ── TAB 5: REPORT ─────────────────────────────────────
    with tab5:
        st.subheader("📄 Performance Report")
        report_text = generate_report(
            instructions, metrics_on, metrics_off, stalls_on, stalls_off
        )
        st.code(report_text, language="")
        st.download_button(
            label="⬇️ Download Report (.txt)",
            data=io.BytesIO(report_text.encode("utf-8")),
            file_name="pipeline_report.txt",
            mime="text/plain",
            use_container_width=True,
        )