import streamlit as st
import pandas as pd
import time
import io

try:
    from core.parser import parse_instructions
    from core.pipeline_engine import Pipeline
    from performance.metrics import calculate_metrics
except ImportError as e:
    st.error(f"❌ ไม่สามารถโหลด Core Logic ได้: {e}")

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
    return df

def count_stalls(df):
    """
    ตรวจ stall จาก 2 วิธี:
    1. มีค่า "STALL" ใน cell (engine บางตัวเขียนไว้ชัดเจน)
    2. EX ว่าง ("") แต่ MEM ไม่ว่าง — bubble ที่ถูก insert
    """
    total, details = 0, []
    for _, row in df.iterrows():
        cycle = row.get("Cycle", "?")
        is_stall = False

        # วิธี 1: มี "STALL" string
        for s in STAGES:
            if str(row.get(s, "")).strip() == "STALL":
                is_stall = True
                break

        # วิธี 2: EX ว่าง แต่ MEM และ WB ไม่ว่าง (bubble ถูก insert)
        if not is_stall:
            ex_empty  = str(row.get("EX",  "")).strip() == ""
            mem_full  = str(row.get("MEM", "")).strip() not in ("", "STALL")
            id_full   = str(row.get("ID",  "")).strip() not in ("", "STALL")
            if ex_empty and mem_full and id_full:
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

    return (
        f'<div style="background:#fafafa;padding:20px;border:1px solid #ddd;border-radius:12px;">'
        f'<h4 style="color:#333;margin:0 0 12px 0;">⏱ Cycle: {current} / {max_c}</h4>'
        f'<hr style="margin-bottom:12px;">{rows_html}</div>'
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
<div style="text-align:center;padding:40px 0 28px 0;">
    <div style="display:inline-block;background:linear-gradient(135deg,#eef2ff,#e0e7ff);
                border:1px solid #c7d2fe;border-radius:20px;padding:5px 16px;
                font-size:12px;font-weight:700;color:#6366f1;letter-spacing:1px;
                text-transform:uppercase;margin-bottom:18px;">
        Computer Architecture Project
    </div>
    <div style="margin-bottom:14px;">
        <span style="font-size:52px;line-height:1;display:block;margin-bottom:12px;">🚀</span>
        <span style="font-family:'Inter',sans-serif;font-weight:900;font-size:2.6rem;
                     letter-spacing:-1.5px;
                     background:linear-gradient(135deg,#4338ca 0%,#7c3aed 50%,#6366f1 100%);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                     background-clip:text;line-height:1.1;display:block;">
            5-Stage RISC Pipeline Simulator
        </span>
    </div>
    <div style="height:4px;width:80px;background:linear-gradient(90deg,#6366f1,#a855f7,#8b5cf6);
                border-radius:2px;margin:0 auto 16px;"></div>
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
    enable_forwarding = st.checkbox("Enable Data Forwarding", value=True)
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

        if not tl_on:
            st.error("❌ Simulation ผลิตข้อมูลว่างเปล่า")
        else:
            st.session_state.sim_ready    = True
            st.session_state.timeline_on  = tl_on
            st.session_state.timeline_off = tl_off
            st.session_state.instructions = instructions
            st.session_state.step_cycle   = 1
            # เก็บ register state หลัง simulate เสร็จ
            st.session_state.registers    = list(p_on.registers)

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

    timeline = tl_on if enable_forwarding else tl_off
    df_tl  = normalize_df(pd.DataFrame(timeline))
    df_on  = normalize_df(pd.DataFrame(tl_on))
    df_off = normalize_df(pd.DataFrame(tl_off))

    instr_list  = extract_instr_list(df_tl)
    max_c       = int(df_tl["Cycle"].max())
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

        # Hazard summary box — อยู่เหนือ animation เสมอ
        if hazard_pairs and instr_list:
            rows = ""
            for (i, j), label in hazard_pairs.items():
                import html as _html
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
                    padding:12px 16px;margin-bottom:12px;'>
                    <div style='font-weight:700;font-size:14px;margin-bottom:8px;color:#7d5a00;'>
                        ⚠️ RAW Hazards ที่ตรวจพบ</div>
                    {rows}
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

    # ── TAB 2: TIMELINE + STALL ────────────────────────────
    with tab2:
        st.subheader("📊 Timeline Table")

        # Hazard highlight ใน dataframe
        def highlight_hazard(data):
            style = pd.DataFrame("", index=data.index, columns=data.columns)
            for idx, row in data.iterrows():
                has_stall = any(str(row.get(s, "")).strip() == "STALL"
                                for s in STAGES if s in data.columns)
                ex_empty  = str(row.get("EX",  "")).strip() == ""
                mem_full  = str(row.get("MEM", "")).strip() not in ("", "STALL")
                id_full   = str(row.get("ID",  "")).strip() not in ("", "STALL")
                if has_stall or (ex_empty and mem_full and id_full):
                    style.loc[idx] = "background-color: #ffe0e0"
            return style

        styled_df = df_tl.fillna("").style.apply(highlight_hazard, axis=None)
        st.dataframe(styled_df, use_container_width=True)
        st.caption("🔴 แถวสีแดง = cycle ที่มี STALL เกิดขึ้น")

        st.subheader("🔴 Stall Details")
        details = details_on if enable_forwarding else details_off
        if details:
            st.dataframe(pd.DataFrame(details), use_container_width=True)
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

        # ── Timeline คู่กัน high fixed ──
        st.markdown("#### 📋 Timeline Detail")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**✅ With Forwarding**")
            st.dataframe(df_on.fillna(""), use_container_width=True, height=300)
        with col_b:
            st.markdown("**❌ Without Forwarding**")
            st.dataframe(df_off.fillna(""), use_container_width=True, height=300)

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

        # ไฮไลต์ register ที่ไม่ใช่ 0 (มีการเขียน)
        def highlight_nonzero(row):
            return ["background-color: #e8f5e9" if row["Value (Dec)"] != 0 else ""
                    for _ in row]

        st.dataframe(
            df_reg.style.apply(highlight_nonzero, axis=1),
            use_container_width=True,
            height=400,
        )
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