import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面配置
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# --- 2. 增强型 CSS：修复折叠按钮可见性与布局 ---
st.markdown("""
    <style>
    /* 确保侧边栏折叠按钮（那个 > 符号）永远可见且在最顶层 */
    .st-emotion-cache-hp08ih {
        z-index: 999999 !important;
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 0 5px 5px 0 !important;
    }
    
    /* 移除主区域留白 */
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    header {visibility: hidden;} 
    footer {visibility: hidden;}

    /* 侧边栏宽度与样式 */
    section[data-testid="stSidebar"] {
        width: 350px !important; 
        background-color: #111111;
    }

    /* 表格态按钮精细化 */
    .stButton > button {
        border-radius: 2px;
        border: 1px solid #333;
        margin-bottom: -2px;
        text-align: left;
        padding: 4px 8px;
        background-color: #1a1a1a;
        color: #efefef;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 账户设置 (折叠式) ---
with st.sidebar:
    with st.expander("👤 账户设置", expanded=False):
        try:
            default_user = st.secrets["GEONAMES_USER"]
        except:
            default_user = ""
        gn_user = st.text_input("GeoNames Username", value=default_user, type="password")
        st.caption("用户名已加密存储在 Secrets 中")

# 初始化状态
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

# --- 4. 检索控制台 ---
with st.sidebar:
    st.subheader("🔍 检索控制台")
    place_name = st.text_input("输入地名 (拼音/英文)", "zhengzhou", label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    with c1:
        search_btn = st.button("开始查询", use_container_width=True)
    with c2:
        if st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

    # 检索逻辑
    if search_btn and gn_user:
        with st.spinner('Searching...'):
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
                else:
                    st.warning("No results.")
            except:
                st.error("API Error")

    # 表格态结果显示
    if st.session_state.search_results:
        st.markdown("---")
        # 表头
        h1, h2, h3 = st.columns([1, 6, 2])
        h1.caption("#")
        h2.caption("地名 (点击定位)")
        h3.caption("国家")
        
        for i, res in enumerate(st.session_state.search_results):
            col1, col2, col3 = st.columns([1, 6, 2])
            col1.write(f"**{i+1}**")
            if col2.button(f"{res['Name']}", key=f"p_{i}", use_container_width=True):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 14
            col3.write(f"`{res['Country']}`")

# --- 5. 右侧全屏地图 ---
# 确保地图容器高度充满
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
    tiles=None
)

# 三种底图
folium.TileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', 
                 attr='CartoDB', name='CartoDB (简约白)', show=True).add_to(m)
folium.TileLayer('openstreetmap', name='OSM (标准版)').add_to(m)
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='Esri (卫星影像)').add_to(m)

# 标记点
if st.session_state.search_results:
    for res in st.session_state.search_results:
        folium.Marker([res['Lat'], res['Lon']], tooltip=res['Name']).add_to(m)

folium.LayerControl(position='bottomleft').add_to(m)

# 渲染地图
st_folium(m, width=2000, height=1000, key="main_map")
