import streamlit as st
import pandas as pd
import time

# นำเข้า Logic
try:
    from core.parser import parse_instructions
    from core.pipeline_engine import Pipeline
    from performance.metrics import calculate_metrics
except ImportError as e:
    st.error(f"❌ ไม่สามารถโหลด Core Logic ได้: {e}")

st.set_page_config(page_title="RISC Pipeline Simulator", layout="wide", page_icon="🚀")

# --- 1. CONFIG & STYLES ---
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
STAGE_COLORS = {
    "IF":    "#4FC3F7",
    "ID":    "#81C784",
    "EX":    "#FFD54F",
    "MEM":   "#FFB74D",
    "WB":    "#E57373",
    "STALL": "#B0BEC5",
    "":      "#f0f0f0",
}

# --- 2. HEADER ---
st.markdown("<h1 style='text-align:center;'>🚀 5-Stage RISC Pipeline Simulator</h1>", unsafe_allow_html=True)
st.divider()

# --- 3. INPUT AREA ---
left, right = st.columns([2, 1])
with left:
    default_program = "ADD $s0, $t1, $t2\nSUB $s1, $s0, $t0\nLW $t2, 0($s1)\nSW $t2, 4($s0)"
    instruction_text = st.text_area("📝 Instructions", default_program, height=180)

with right:
    st.markdown("### ⚙️ Settings")
    enable_forwarding = st.checkbox("Enable Forwarding", value=True)
    anim_speed = st.slider("Animation Speed (sec/cycle)", 0.1, 1.5, 0.4, 0.1)
    run = st.button("▶ Run Simulation", use_container_width=True)

st.divider()

# --- 4. MAIN LOGIC ---
if run:
    try:
        instructions = parse_instructions(instruction_text)
        pipeline = Pipeline(instructions, enable_forwarding)
        timeline = pipeline.run()

        if not timeline:
            st.error("❌ Simulation ผลิตข้อมูลว่างเปล่า กรุณาเช็คคำสั่ง Instruction")
        else:
            df_tl = pd.DataFrame(timeline)

            # ---- FIX 1: หา instruction list จากทุก stage ไม่ใช่แค่ IF ----
            all_instrs = []
            for s in STAGES:
                if s in df_tl.columns:
                    vals = df_tl[s].dropna().unique().tolist()
                    for v in vals:
                        if v and v not in all_instrs and str(v).strip() not in ("", "STALL"):
                            all_instrs.append(v)

            # fallback: ถ้า engine ใช้คอลัมน์ 'instruction' หรือ 'Instruction'
            if not all_instrs:
                for col in ["instruction", "Instruction", "instr"]:
                    if col in df_tl.columns:
                        all_instrs = df_tl[col].dropna().unique().tolist()
                        break

            # ---- FIX 2: หา max cycle ----
            if "Cycle" in df_tl.columns:
                max_c = int(df_tl["Cycle"].max())
            elif "cycle" in df_tl.columns:
                max_c = int(df_tl["cycle"].max())
                df_tl = df_tl.rename(columns={"cycle": "Cycle"})
            else:
                max_c = len(df_tl)
                df_tl["Cycle"] = range(1, max_c + 1)

            st.subheader("🎬 Pipeline Animation")

            # ---- FIX 3: ใช้ st.empty() นอก loop และ overwrite ด้วย container ----
            anim_placeholder = st.empty()

            if not all_instrs:
                st.warning("⚠️ ไม่พบรายชื่อ Instruction ใน timeline — ตรวจสอบ column names ของ pipeline.run()")
                st.dataframe(df_tl, use_container_width=True)
            else:
                progress_bar = st.progress(0)

                for current in range(1, max_c + 1):
                    # build HTML ทั้งก้อนก่อน แล้ว render ครั้งเดียว
                    rows_html = ""
                    for instr in all_instrs:
                        cells = ""
                        for c in range(1, max_c + 1):
                            stg = ""
                            target = df_tl[df_tl["Cycle"] == c]
                            if not target.empty:
                                row = target.iloc[0]
                                for s in STAGES:
                                    if s in row and row[s] == instr:
                                        stg = s
                                        break

                            is_current = (c == current)
                            is_past    = (c < current)
                            has_stage  = bool(stg)

                            bg      = STAGE_COLORS.get(stg, "#f0f0f0") if has_stage else "#f0f0f0"
                            opacity = "1.0" if is_current else ("0.4" if is_past else "0.06")
                            border  = "2px solid #222" if (is_current and has_stage) else "1px solid #ddd"
                            label   = stg if (is_current or is_past) else ""
                            shadow  = "box-shadow:0 0 6px rgba(0,0,0,0.25);" if (is_current and has_stage) else ""

                            cells += (
                                f'<div style="width:48px;height:34px;background:{bg};opacity:{opacity};'
                                f'border:{border};margin:2px;display:flex;justify-content:center;'
                                f'align-items:center;font-size:11px;font-weight:bold;border-radius:6px;{shadow}">'
                                f'{label}</div>'
                            )

                        rows_html += (
                            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
                            f'<div style="width:190px;font-family:monospace;font-size:13px;'
                            f'color:#333;font-weight:bold;padding-right:8px;">{instr}</div>'
                            f'{cells}</div>'
                        )

                    html = (
                        f'<div style="background:#fafafa;padding:20px;border:1px solid #ddd;'
                        f'border-radius:12px;">'
                        f'<h4 style="color:#333;margin:0 0 12px 0;">⏱ Cycle: {current} / {max_c}</h4>'
                        f'<hr style="margin-bottom:12px;">'
                        f'{rows_html}'
                        f'</div>'
                    )

                    # ---- FIX 4: render ใน with block เพื่อให้ flush ทันที ----
                    with anim_placeholder.container():
                        st.markdown(html, unsafe_allow_html=True)

                    progress_bar.progress(current / max_c)

                    # ---- FIX 5: ใช้ time.sleep() น้อยลง + ปล่อยให้ user ปรับได้ ----
                    time.sleep(anim_speed)

                progress_bar.empty()
                st.success("✅ Simulation Complete!")

            # --- 5. SUMMARY ---
            st.divider()
            col_table, col_metrics = st.columns([2, 1])

            with col_table:
                st.subheader("📊 Timeline Table")
                st.dataframe(df_tl.fillna(""), use_container_width=True)

            with col_metrics:
                st.subheader("📈 Performance")
                metrics = calculate_metrics(timeline)
                m1, m2 = st.columns(2)
                m1.metric("Total Cycles", metrics.get("cycles", max_c))
                m2.metric("CPI", round(metrics.get("cpi", 0), 2))
                st.metric("Total Instructions", len(instructions))

    except Exception as e:
        st.error(f"⚠️ Simulation Error: {e}")
        st.exception(e)