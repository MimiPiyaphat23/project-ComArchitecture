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
    "IF": "#4FC3F7", "ID": "#81C784", "EX": "#FFD54F", 
    "MEM": "#FFB74D", "WB": "#E57373", "STALL": "#B0BEC5", "": "#f0f0f0"
}

# --- 2. HEADER ---
st.markdown("<h1 style='text-align:center;'>🚀 5-Stage RISC Pipeline Simulator</h1>", unsafe_allow_html=True)
st.divider()

# --- 3. INPUT AREA ---
left, right = st.columns([2,1])
with left:
    default_program = "ADD $s0, $t1, $t2\nSUB $s1, $s0, $t0\nLW $t2, 0($s1)\nSW $t2, 4($s0)"
    instruction_text = st.text_area("📝 Instructions", default_program, height=180)

with right:
    st.markdown("### ⚙️ Settings")
    enable_forwarding = st.checkbox("Enable Forwarding", value=True)
    run = st.button("▶ Run Simulation", use_container_width=True)

st.divider()

# --- 4. MAIN LOGIC ---
# --- แก้ไขส่วนการวาด Animation ภายใน if run: ---
if run:
    try:
        instructions = parse_instructions(instruction_text)
        pipeline = Pipeline(instructions, enable_forwarding)
        timeline = pipeline.run()

        if not timeline:
            st.error("❌ ไม่พบข้อมูล Timeline")
        else:
            df_tl = pd.DataFrame(timeline)
            # หา Cycle สูงสุดจากข้อมูลจริงในตาราง
            max_c = int(df_tl['Cycle'].max()) if 'Cycle' in df_tl.columns else 0
            # ดึงคำสั่งที่ไม่ซ้ำกันออกมาเรียงลำดับ
            instr_list = df_tl['IF'].dropna().unique().tolist()

            st.subheader("🎬 Pipeline Animation")
            anim_placeholder = st.empty()
            
            for current in range(1, max_c + 1):
                # เริ่มสร้าง HTML Container
                html = f"<div style='background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd;'>"
                html += f"<h4 style='margin:0 0 15px 0;'>Cycle: {current} / {max_c}</h4>"
                
                for instr in instr_list:
                    html += "<div style='display: flex; align-items: center; margin-bottom: 8px;'>"
                    # ส่วนแสดงชื่อ Instruction
                    html += f"<div style='width: 180px; font-family: monospace; font-weight: bold; font-size: 14px;'>{instr}</div>"
                    
                    for c in range(1, max_c + 1):
                        # หา Stage ณ Cycle นั้นๆ จาก DataFrame
                        stg = ""
                        target_row = df_tl[df_tl['Cycle'] == c]
                        if not target_row.empty:
                            for s in STAGES:
                                if target_row.iloc[0].get(s) == instr:
                                    stg = s
                                    break
                        
                        # กำหนดสไตล์กล่อง
                        is_active = (c == current)
                        is_past = (c < current)
                        bg = STAGE_COLORS.get(stg, "#f0f0f0") if (is_active or is_past) else "#f0f0f0"
                        op = "1.0" if is_active else ("0.3" if is_past else "0.05")
                        bd = "2px solid #333" if is_active and stg else "1px solid #eee"
                        txt = "black" if (is_active or is_past) else "transparent"
                        
                        # วาดกล่อง Stage แบบ Clean HTML
                        html += f'<div style="width: 45px; height: 32px; background-color: {bg}; opacity: {op}; border: {bd}; margin: 2px; display: flex; justify-content: center; align-items: center; font-size: 10px; font-weight: bold; border-radius: 5px; color: {txt};">{stg}</div>'
                    
                    html += "</div>" # ปิดแถว Instruction
                
                html += "</div>" # ปิด Container ใหญ่
                
                # พ่น HTML ลงหน้าจอ
                anim_placeholder.markdown(html, unsafe_allow_html=True)
                time.sleep(0.4)

            st.success("✅ Simulation Complete!")
            
            # แสดง Metrics และ Table ตามปกติ
            st.divider()
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("📊 Timeline Table")
                st.dataframe(df_tl.fillna(""), use_container_width=True)
            with col2:
                st.subheader("📈 Performance")
                metrics = calculate_metrics(timeline)
                st.metric("Total Cycles", metrics.get("cycles", max_c))
                st.metric("CPI", round(metrics.get("cpi", 0), 2))

    except Exception as e:
        st.error(f"⚠️ Simulation Error: {e}")