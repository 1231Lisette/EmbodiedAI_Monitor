import streamlit as st
import pandas as pd
from src.database import Database
import webbrowser

# 页面配置
st.set_page_config(page_title="Embodied AI Monitor", page_icon="🤖", layout="wide")

# 自定义 CSS 让界面更像 Notion/Apple 风格
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
    .score-high { color: #dc2626; font-weight: bold; }
    .score-mid { color: #d97706; font-weight: bold; }
    .tag {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-right: 5px;
    }
    .ai-comment {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 10px;
        margin: 10px 0;
        color: #1e3a8a;
        font-size: 0.95em;
    }
</style>
""", unsafe_allow_html=True)

# 初始化数据库
db = Database()

# 侧边栏：过滤器
st.sidebar.title("🔍 筛选控制台")
min_score = st.sidebar.slider("最低 AI 评分", 0, 10, 6)
search_query = st.sidebar.text_input("搜索关键词")
show_read = st.sidebar.checkbox("显示已读", False)

# 获取数据
items = db.fetch_items(min_score=min_score)
df = pd.DataFrame(items)

# 过滤逻辑
if search_query:
    df = df[df['title'].str.contains(search_query, case=False) | df['abstract'].str.contains(search_query, case=False)]
if not show_read and 'is_read' in df.columns:
    df = df[df['is_read'] == 0]

# 主界面
st.title("🤖 Embodied AI Monitor Pro")
st.caption(f"共找到 {len(df)} 条高价值情报 (AI Score >= {min_score})")

# 展示列表
for idx, row in df.iterrows():
    with st.container():
        # 卡片容器
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 标题行
            score_color = "score-high" if row['ai_score'] >= 8 else "score-mid"
            st.markdown(f"### [{row['ai_score']}分] {row['title']}")
            
            # 标签
            tags_html = "".join([f"<span class='tag'>{t}</span>" for t in row['tags']])
            st.markdown(f"<div>{tags_html} <span style='color:#94a3b8; font-size:0.8em'>| {row['date']} | {row['source']}</span></div>", unsafe_allow_html=True)
            
            # AI 锐评 (这是核心价值！)
            if row['ai_comment']:
                st.markdown(f"<div class='ai-comment'>💡 <b>AI 锐评：</b>{row['ai_comment']}</div>", unsafe_allow_html=True)
            
            # 摘要 (可折叠)
            with st.expander("查看摘要"):
                st.write(row['abstract'])
                
            # 笔记区域 (交互功能)
            user_note = st.text_area("我的笔记", value=row['user_notes'] if row['user_notes'] else "", key=f"note_{row['id']}", height=70)
            if st.button("💾 保存笔记", key=f"save_{row['id']}"):
                db.update_user_interaction(row['id'], notes=user_note)
                st.toast("笔记已保存！")

            # 操作按钮
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                if st.button("✅ 标为已读", key=f"read_{row['id']}"):
                    db.update_user_interaction(row['id'], is_read=1)
                    st.rerun()
            with c2:
                if st.button("🔗 原文链接", key=f"link_{row['id']}"):
                    webbrowser.open_new_tab(row['url'])

        with col2:
            # 视觉预览 (如果有图就显示，没有就显示来源Logo)
            if row['media_url']:
                st.image(row['media_url'], use_column_width=True)
            else:
                # 占位图
                st.markdown("📷 *No Preview*")

        st.markdown("---")