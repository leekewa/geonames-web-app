import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面基础配置
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# --- 2. 增强型 CSS：解决比例尺溢出与把手可见性 ---
st.markdown("""
    <style>
    .block-container { padding: 0rem !important; max-width: 100% !important; }
    header, footer {visibility: hidden;}

    /* 侧边栏把手：亮青色悬浮按钮 */
    button[data-testid="sidebar-button"] {
        background-color: #00d4ff !important; 
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        width: 45px !important;
        height: 45px !important;
        left: 0px !important;
        top: 20px !important;
        z-index: 10000 !important;
        box-shadow: 3px 3px 12px rgba(0,0,0,0.4) !important;
    }
    
    section[data-testid="stSidebar"] { background-color: #111111 !important; width: 380px !important; }

    /* 修复比例尺溢出：给地图容器底部留出安全空间 */
    .stFolium { margin-bottom: 30px !important; }

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

# --- 3. 安全读取账户与初始化状态 ---
try:
    default_user = st.secrets["GEONAMES_USER"]
except:
    default_user = ""

if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

# --- 4. 左侧侧边栏 ---
with st.sidebar:
    st.title("🌍 检索控制台")
    with st.expander("👤 账户设置", expanded=False):
        gn_user = st.text_input("Username", value=default_user, type="password")

    st.markdown("---")
    place_name = st.text_input("输入地名 (拼音/英文)", "zhengzhou")
    
    col1, col2 = st.columns(2)
    with col1:
        search_btn = st.button("开始查询", use_container_width=True)
    with col2:
        if st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

# 处理检索逻辑
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
        st.sidebar.error(f"Error: {e}")

# 显示结果列表
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

# --- 5. 地图渲染（修复底图重置问题） ---
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
    tiles=None # 必须设为 None
)

# 定义底图图层
layer_carto = folium.TileLayer(
    tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', 
    attr='CartoDB', name='简约白', overlay=False, control=True
)
layer_osm = folium.TileLayer('openstreetmap', name='OSM 标准', overlay=False, control=True)
layer_esri = folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
    attr='Esri', name='卫星影像', overlay=False, control=True
)

# 核心修正：默认先添加所有图层，Folium 会按顺序显示第一个，除非你手动切换
# 注意：在 Streamlit 中，如果不使用特定的底图保存插件，重绘时默认底图是由添加顺序决定的。
# 我们将“简约白”放在第一顺位，确保重置时它始终是默认。
layer_carto.add_to(m)
layer_osm.add_to(m)
layer_esri.add_to(m)

# 标记点
for res in st.session_state.search_results:
    folium.Marker([res['Lat'], res['Lon']], tooltip=res['Name']).add_to(m)

folium.LayerControl(position='bottomleft').add_to(m)

# 渲染地图：height 略微调小至 920，配合 CSS 的 margin 防止比例尺被切断
st_folium(m, width=2000, height=920, key="main_map")
