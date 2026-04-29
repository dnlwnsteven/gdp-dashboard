import streamlit as st
import pandas as pd

# ================= 1. 页面基本设置 =================
st.set_page_config(page_title="转载数据标注平台", layout="wide", page_icon="🎯")

# ================= 2. 状态缓存 =================
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

# ================= 3. 左侧边栏：控制中心 =================
with st.sidebar:
    st.header("📁 数据看板")
    uploaded_file = st.file_uploader("上传数据文件 (CSV)", type=['csv'])
    
    if uploaded_file is not None and st.session_state.df is None:
        df = pd.read_csv(uploaded_file)
        # 自动补齐标注列
        if '是否有效' not in df.columns:
            df['是否有效'] = ''
        if '水印' not in df.columns:
            df['水印'] = ''
            
        st.session_state.df = df
        st.session_state.current_idx = 0

    if st.session_state.df is not None:
        df = st.session_state.df
        total = len(df)
        annotated = len(df[df['是否有效'] != ''])
        
        st.write(f"📊 **整体进度**: {annotated} / {total}")
        st.progress(annotated / total if total > 0 else 0)
        
        # ---------------- 序号跳转点阵 ----------------
        st.divider()
        st.subheader("📍 进度索引")
        
        with st.container(height=300):
            cols = st.columns(5) # 每行显示5个圆点
            for i, r in df.iterrows():
                status_val = str(r.get('是否有效', '')).strip()
                
                # 颜色逻辑：空是灰，待处理是红，其他是绿
                if status_val == "":
                    label = f"⚪ {i+1}"
                elif status_val == "待处理":
                    label = f"🔴 {i+1}"
                else:
                    label = f"🟢 {i+1}"
                
                if cols[i % 5].button(label, key=f"dot_{i}"):
                    st.session_state.current_idx = i
                    st.rerun()
        
        st.caption("提示：⚪未标 | 🟢已标")

        st.divider()
        # 序号跳转输入
        jump_no = st.number_input("跳转行号", min_value=1, max_value=total, value=st.session_state.current_idx + 1)
        if st.button("确定跳转", use_container_width=True):
            st.session_state.current_idx = jump_no - 1
            st.rerun()

        st.divider()
        # 导出功能
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出标注结果", data=csv, file_name="标注结果_export.csv", mime="text/csv", type="primary", use_container_width=True)

# ================= 4. 主界面：标注窗口 =================
st.title("🎯 转载数据标注平台")

if st.session_state.df is not None:
    df = st.session_state.df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    # 顶部信息：提取 ID 和 来源 (兼容 ord. 前缀)
    d_id = row.get('ord.id', row.get('id', '未知ID'))
    d_src = row.get('ord.source', row.get('source', '未知'))
    st.markdown(f"**当前行号：** {idx + 1} / {len(df)} ｜ **数据 ID：** `{d_id}` ｜ **来源：** `{d_src}`")
    st.divider()
    
    # --- 图片/网页展示区 (三列并行) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🖼️ muri (预览图)")
        m_url = row.get('muri', '')
        if pd.notna(m_url) and str(m_url).startswith('http'):
            st.image(m_url, use_container_width=True)
        else:
            st.warning("无 muri 链接")
            
    with col2:
        st.subheader("🔗 ord.uri (原图)")
        # 这里的解析逻辑确保回来了！
        u_url = row.get('ord.uri', row.get('uri', ''))
        if pd.notna(u_url) and str(u_url).startswith('http'):
            st.image(u_url, use_container_width=True)
            st.caption(f"[查看原图直链]({u_url})")
        else:
            st.info("此条数据无 ord.uri 链接")

    with col3:
        st.subheader("🌐 ord.page (网页)")
        p_url = row.get('ord.page', '')
        if p_url and str(p_url).startswith('http'):
            st.info(f"🔗 [在新标签页打开网页]({p_url})")
            st.caption("请点击链接核对网页实际内容")
        else:
            st.warning("无网页链接")

    # --- 标注操作区 ---
    st.divider()
    with st.expander("📝 标注选项", expanded=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            eff_opts = ["", "有效数据", "电影宣传图", "有水印", "无效数据", "不一样的图", "空白", "待处理"]
            curr_eff = row.get('是否有效', "")
            effectiveness = st.selectbox("1. 是否有效", options=eff_opts, index=eff_opts.index(curr_eff) if curr_eff in eff_opts else 0)
        with c2:
            wm_opts = ["", "无", "视觉中国", "新华网", "中新社", "图虫", "人民日报", "央视总台", "其他水印"]
            curr_wm = row.get('水印', "")
            watermark = st.selectbox("2. 水印类型", options=wm_opts, index=wm_opts.index(curr_wm) if curr_wm in wm_opts else 0)
        with c3:
            st.write(" ")
            if st.button("💾 保存/下一张", type="primary", use_container_width=True):
                st.session_state.df.at[idx, '是否有效'] = effectiveness
                st.session_state.df.at[idx, '水印'] = watermark
                if idx < len(df) - 1:
                    st.session_state.current_idx += 1
                st.rerun()

    # 底部翻页按钮
    nb1, _, nb3 = st.columns([1, 4, 1])
    if nb1.button("⬅️ 上一张") and idx > 0:
        st.session_state.current_idx -= 1
        st.rerun()
    if nb3.button("下一张 ➡️") and idx < len(df) - 1:
        st.session_state.current_idx += 1
        st.rerun()
else:
    st.info("👋 欢迎！请在左侧上传 CSV 数据文件开始标注。")