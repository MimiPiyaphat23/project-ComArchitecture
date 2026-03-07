import streamlit as st
import pandas as pd
import time

# นำเข้า Logic (พยายามรักษาโครงสร้างเดิมของคุณไว้)
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
if run:
    try:
        # 1. คำนวณข้อมูลจาก Engine
        instructions = parse_instructions(instruction_text)
        pipeline = Pipeline(instructions, enable_forwarding)
        timeline = pipeline.run()

        if not timeline:
            st.error("❌ Simulation ผลิตข้อมูลว่างเปล่า กรุณาเช็คคำสั่ง Instruction")
        else:
            # แปลง timeline เป็น DataFrame เพื่อให้จัดการข้อมูลที่กระจัดกระจายได้ง่าย
            df_tl = pd.DataFrame(timeline)
            
            # 2. ส่วน Animation (ปรับปรุงให้รองรับตารางแบบ Cycle-based)
            st.subheader("🎬 Pipeline Animation")
            
            # หาจำนวน Cycle ทั้งหมดจากคอลัมน์ 'Cycle'
            max_c = int(df_tl['Cycle'].max()) if 'Cycle' in df_tl.columns else 0
            
            # ดึงรายชื่อคำสั่งทั้งหมดออกมาเรียงลำดับ (ใช้คอลัมน์ IF เป็นหลัก)
            instr_list = df_tl['IF'].dropna().unique().tolist()
            
            anim_placeholder = st.empty()
            
            for current in range(1, max_c + 1):
                html = f"<div style='background:#ffffff; padding:20px; border:1px solid #ddd; border-radius:10px;'>"
                html += f"<h4 style='color:#333;'>Cycle: {current} / {max_c}</h4><hr>"
                
                for instr in instr_list:
                    html += "<div style='display:flex; align-items:center; margin-bottom:8px;'>"
                    html += f"<div style='width:180px; font-family:monospace; font-size:13px; color:#444;'><b>{instr}</b></div>"
                    
                    for c in range(1, max_c + 1):
                        # ค้นหาว่า ณ Cycle 'c' คำสั่ง 'instr' นี้อยู่ที่ Stage ไหน
                        stg = ""
                        # ตรวจสอบทุก Stage ในแถวที่ตรงกับ Cycle ปัจจุบัน
                        target_row = df_tl[df_tl['Cycle'] == c]
                        if not target_row.empty:
                            for s in STAGES: # ["IF", "ID", "EX", "MEM", "WB"]
                                if target_row.iloc[0].get(s) == instr:
                                    stg = s
                                    break
                        
                        is_current = (c == current)
                        is_past = (c < current)
                        
                        # กำหนดสีและ Effect
                        bg_color = STAGE_COLORS.get(stg, "#f0f0f0") if stg else "#f0f0f0"
                        opacity = "1.0" if is_current else ("0.3" if is_past else "0.05")
                        border = "2px solid #333" if is_current and stg else "1px solid #eee"
                        
                        html += f"""
                        <div style="width:45px; height:32px; background:{bg_color}; opacity:{opacity}; 
                                    border:{border}; margin:2px; display:flex; justify-content:center; 
                                    align-items:center; font-size:10px; font-weight:bold; border-radius:5px;">
                            {stg if (is_current or is_past) else ""}
                        </div>"""
                    html += "</div>"
                
                anim_placeholder.markdown(html + "</div>", unsafe_allow_html=True)
                time.sleep(0.5) 
            
            st.success("✅ Simulation Complete!")

            # 3. ส่วนสรุป (Table & Metrics)
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