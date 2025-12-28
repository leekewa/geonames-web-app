import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面配置
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# --- 2. 核心 CSS：自定义浮动把手与布局优化 ---
st.markdown("""
    <style>
    /* 移除主区域所有边距 */
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    header, footer {visibility: hidden;}

    /* 强制显示并自定义 Streamlit 原生的侧边栏按钮（把手） */
    /* 我们给它一个明显的背景色和阴影，确保它永远浮在地图最上层 */
    button[data-testid="sidebar-button"] {
        background-color: #ff4b4b !important; /* 醒目的红色把手 */
        color: white !important;
        border-radius: 0 5px 5px 0 !important;
        width: 40px !important;
        height: 40px !important;
        left: 0px !important;
        top: 10px !important;
        z-index: 999999 !important; /* 确保在地图之上 */
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5) !important;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #111111 !important;
        width: 350px !important;
    }

    /* 结果列表按钮样式：表格态 */
    .stButton > button {
        border-radius: 0px;
        border: 1px solid #333;
        margin-bottom: -1px;
        text-align: left;
        padding: 5px 10px;
        background-color: #1a1a1a;
        color: #ddd;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 侧边栏：检索面板 ---
with st.sidebar:
    st.title("🌍 检索控制台")
    
    # 账户设置
    with st.expander("👤 账户设置", expanded=False):
        try:
            default_user = st.secrets["GEONAMES_USER"]
        except:
            default_user = ""
        gn_user = st.text_input("Username", value=default_user, type="password")

    st.markdown("---")
    place_name = st.text_input("输入地名 (拼音/英文)", "zhengzhou")
    
    col1, col2 = st.columns(2)
    with c1 := col1.container():
        search_btn = st.button("开始查询", use_container_width=True)
    with c2 := col2.container():
        if 'search_results' in st.session_state and st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

# 初始化状态逻辑
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

# 处理搜索请求
if search_btn and gn_user:
    s_url = 'http://api.geonames.org/searchJSON'
    try:
        s_res = requests.get(s_url, params={'q': place_name, 'username': gn_user, 'maxRows': 15}).json()
        places = s_res.get('geonames', [])
        if places:
            st.session_state.search_results = [
                {"Name": p.get('name'), "Country": p.get('countryCode'), 
                 "Lat": float(p.get('lat')), "Lon": float(p.get('lng'))} for p in places
            ]
            st.session_state.map_center = [st.session_state.search_results[0]['Lat'], st.session_state.search_results[0]['Lon']]
            st.session_state.map_zoom = 11
            st.rerun()
    except:
        st.sidebar.error("API 调用失败")

# 侧边栏：结果列表
with st.sidebar:
    if st.session_state.search_results:
        st.markdown("### 搜索结果")
        h1, h2, h3 = st.columns([1, 6, 2])
        h1.caption("#")
        h2.caption("地名 (点击定位)")
        h3.caption("国家")
        
        for i, res in enumerate(st.session_state.search_results):
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f"**{i+1}**")
            if c2.button(f"{res['Name']}", key=f"btn_{i}", use_container_width=True):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 14
                st.rerun()
            c3.write(f"`{res['Country']}`")

# --- 4. 右侧地图区域 ---
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
    tiles=None
)

# 基础底图
folium.TileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', 
                 attr='CartoDB', name='简约白', show=True).add_to(m)
folium.TileLayer('openstreetmap', name='OSM 标准').add_to(m)
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='卫星影像').add_to(m)

# 标记点
for res in st.session_state.search_results:
    folium.Marker([res['Lat'], res['Lon']], tooltip=res['Name']).add_to(m)

# 控件置于左下角，避免遮挡左上角的把手
folium.LayerControl(position='bottomleft').add_to(m)

# 满屏渲染
st_folium(m, width=2000, height=1000, key="main_map")
