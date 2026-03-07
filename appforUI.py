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

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
STAGE_COLORS = {
    "IF": "#4FC3F7", "ID": "#81C784", "EX": "#FFD54F",
    "MEM": "#FFB74D", "WB": "#E57373", "STALL": "#B0BEC5", "": "#f0f0f0",
}

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
    total, details = 0, []
    for s in STAGES:
        if s in df.columns:
            for _, row in df[df[s] == "STALL"].iterrows():
                total += 1
                details.append({"Cycle": row.get("Cycle", "?"), "Stage": s})
    return total, details

def build_animation_html(df, instr_list, current, max_c):
    rows_html = ""
    for instr in instr_list:
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
        rows_html += (
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<div style="width:190px;font-family:monospace;font-size:13px;color:#333;'
            f'font-weight:bold;padding-right:8px;">{instr}</div>{cells}</div>'
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
st.markdown("<h1 style='text-align:center;'>🚀 5-Stage RISC Pipeline Simulator</h1>",
            unsafe_allow_html=True)
st.divider()

# ─────────────────────────────────────────────
# INPUT AREA
# ─────────────────────────────────────────────
left, right = st.columns([2, 1])
with left:
    default_program = "ADD $s0, $t1, $t2\nSUB $s1, $s0, $t0\nLW $t2, 0($s1)\nSW $t2, 4($s0)"
    instruction_text = st.text_area("📝 Instructions", default_program, height=180)

with right:
    st.markdown("### ⚙️ Settings")
    enable_forwarding = st.checkbox("Enable Forwarding", value=True)
    anim_speed = st.slider("Animation Speed (sec/cycle)", 0.1, 1.5, 0.4, 0.1)
    mode = st.radio("Mode", ["▶ Auto Run", "⏯ Step-by-step"], horizontal=True)
    run = st.button("▶ Run Simulation", use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# MAIN LOGIC
# ─────────────────────────────────────────────

# กด Run → คำนวณใหม่ แล้วเก็บทุกอย่างใน session_state
if run:
    try:
        instructions = parse_instructions(instruction_text)
        tl_on  = Pipeline(instructions, forwarding_enabled=True).run()
        tl_off = Pipeline(instructions, forwarding_enabled=False).run()

        if not tl_on:
            st.error("❌ Simulation ผลิตข้อมูลว่างเปล่า")
        else:
            # เก็บผลไว้ใน session_state — จะยังอยู่แม้กด Prev/Next
            st.session_state.sim_ready    = True
            st.session_state.timeline_on  = tl_on
            st.session_state.timeline_off = tl_off
            st.session_state.instructions = instructions
            st.session_state.step_cycle   = 1  # reset เมื่อ Run ใหม่

    except Exception as e:
        st.error(f"⚠️ Simulation Error: {e}")
        st.exception(e)

# แสดงผลเมื่อมีข้อมูล (ทั้งตอน Run ครั้งแรก และตอนกด Prev/Next)
if st.session_state.get("sim_ready"):

    tl_on        = st.session_state.timeline_on
    tl_off       = st.session_state.timeline_off
    instructions = st.session_state.instructions

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

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎬 Animation", "📊 Timeline", "⚖️ Comparison", "📄 Report"
    ])

    # ── TAB 1: ANIMATION ──────────────────────────────────
    with tab1:
        st.subheader("🎬 Pipeline Animation")

        if not instr_list:
            st.warning("⚠️ ไม่พบ instruction list — เช็ค column names ของ pipeline.run()")
            st.dataframe(df_tl, use_container_width=True)

        elif mode == "⏯ Step-by-step":
            # ── ปุ่มควบคุม ──
            col_prev, col_next, col_restart = st.columns([1, 1, 1])
            with col_prev:
                prev_clicked = st.button("⬅ Prev", use_container_width=True)
            with col_next:
                next_clicked = st.button("Next ➡", use_container_width=True)
            with col_restart:
                restart_clicked = st.button("🔄 Restart", use_container_width=True)

            # อัปเดต step_cycle ตามปุ่มที่กด
            # (การอัปเดตต้องเกิดก่อน render เพื่อให้แสดง cycle ที่ถูกต้อง)
            if restart_clicked:
                st.session_state.step_cycle = 1
            elif prev_clicked and st.session_state.step_cycle > 1:
                st.session_state.step_cycle -= 1
            elif next_clicked and st.session_state.step_cycle < max_c:
                st.session_state.step_cycle += 1

            current = st.session_state.step_cycle

            # ── แสดง animation frame ──
            st.markdown(
                build_animation_html(df_tl, instr_list, current, max_c),
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
                        build_animation_html(df_tl, instr_list, current, max_c),
                        unsafe_allow_html=True
                    )
                progress_bar.progress(current / max_c)
                time.sleep(anim_speed)
            progress_bar.empty()
            st.success("✅ Simulation Complete!")

    # ── TAB 2: TIMELINE + STALL ────────────────────────────
    with tab2:
        st.subheader("📊 Timeline Table")
        st.dataframe(df_tl.fillna(""), use_container_width=True)

        st.subheader("🔴 Stall Details")
        details = details_on if enable_forwarding else details_off
        if details:
            st.dataframe(pd.DataFrame(details), use_container_width=True)
        else:
            st.success("✅ ไม่มี Stall เกิดขึ้น")

    # ── TAB 3: COMPARISON ─────────────────────────────────
    with tab3:
        st.subheader("⚖️ Forwarding vs No Forwarding")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### ✅ With Forwarding")
            st.metric("Total Cycles", metrics_on.get("cycles", int(df_on["Cycle"].max())))
            st.metric("CPI",    round(metrics_on.get("cpi", 0), 4))
            st.metric("Stalls", stalls_on)
            st.dataframe(df_on.fillna(""), use_container_width=True)

        with col_b:
            st.markdown("### ❌ Without Forwarding")
            st.metric("Total Cycles", metrics_off.get("cycles", int(df_off["Cycle"].max())))
            st.metric("CPI",    round(metrics_off.get("cpi", 0), 4))
            st.metric("Stalls", stalls_off)
            st.dataframe(df_off.fillna(""), use_container_width=True)

        saved = stalls_off - stalls_on
        if saved > 0:
            pct = round(saved / max(stalls_off, 1) * 100, 1)
            st.info(f"💡 Forwarding ช่วยลด stall ได้ **{saved} ครั้ง** ({pct}%)")
        else:
            st.info("ℹ️ ไม่มีความแตกต่าง — instruction ชุดนี้ไม่มี hazard")

    # ── TAB 4: REPORT ─────────────────────────────────────
    with tab4:
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