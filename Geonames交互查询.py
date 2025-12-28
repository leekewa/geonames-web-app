import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面基础配置
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# --- 2. 增强型 CSS：自定义悬浮把手与全屏布局 ---
st.markdown("""
    <style>
    /* 移除主区域留白 */
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    header, footer {visibility: hidden;}

    /* 自定义侧边栏把手（那个 > 箭头按钮） */
    /* 强制它显示为高亮的悬浮块，确保关掉后一眼就能看到 */
    button[data-testid="sidebar-button"] {
        background-color: #00d4ff !important; /* 明亮的青蓝色把手 */
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        width: 45px !important;
        height: 45px !important;
        left: 0px !important;
        top: 20px !important;
        z-index: 999999 !important;
        box-shadow: 3px 3px 12px rgba(0,0,0,0.4) !important;
    }
    
    /* 侧边栏样式定制 */
    section[data-testid="stSidebar"] {
        background-color: #111111 !important;
        width: 380px !important;
    }

    /* 结果列表表格态样式 */
    .stButton > button {
        border-radius: 2px;
        border: 1px solid #333;
        margin-bottom: -1px;
        text-align: left;
        padding: 5px 10px;
        background-color: #1a1a1a;
        color: #efefef;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 侧边栏内容 ---
with st.sidebar:
    st.title("🌍 检索控制台")
    
    # 账户设置（折叠显示，不占位）
    with st.expander("👤 账户设置", expanded=False):
        try:
            default_user = st.secrets["GEONAMES_USER"]
        except:
            default_user = ""
        gn_user = st.text_input("Username", value=default_user, type="password")

    st.markdown("---")
    place_name = st.text_input("输入地名 (拼音/英文)", "zhengzhou")
    
    col1, col2 = st.columns(2)
    with col1:
        search_btn = st.button("开始查询", use_container_width=True)
    with col2:
        # 仅在有结果时显示导出按钮
        if 'search_results' in st.session_state and st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

# 4. 初始化与检索逻辑
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

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
    except Exception as e:
        st.sidebar.error(f"API请求失败: {e}")

# 结果列表显示
with st.sidebar:
    if st.session_state.search_results:
        st.markdown("### 搜索结果")
        h1, h2, h3 = st.columns([1, 6, 2])
        h1.caption("#")
        h2.caption("地名 (点击定位)")
        h3.caption("国家码")
        
        for i, res in enumerate(st.session_state.search_results):
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f"**{i+1}**")
            # 点击按钮定位
            if c2.button(f"{res['Name']}", key=f"btn_{i}", use_container_width=True):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 14
                st.rerun()
            c3.write(f"`{res['Country']}`")

# --- 5. 右侧全屏地图显示 ---
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
    tiles=None
)

# 添加三种专业底图
folium.TileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', 
                 attr='CartoDB', name='CartoDB (简约白)', show=True).add_to(m)
folium.TileLayer('openstreetmap', name='OSM (标准版)').add_to(m)
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri', name='Esri (卫星影像)').add_to(m)

# 在地图上打点
for res in st.session_state.search_results:
    folium.Marker([res['Lat'], res['Lon']], tooltip=res['Name']).add_to(m)

# 将底图控件放在左下角，避开左上角的“把手”
folium.LayerControl(position='bottomleft').add_to(m)

# 渲染地图
st_folium(m, width=2000, height=1000, key="main_map")
