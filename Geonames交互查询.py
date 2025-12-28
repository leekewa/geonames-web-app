import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面基础配置：设为 wide 模式以支持全屏感
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# --- 2. 深度定制 CSS：解决比例尺溢出、把手显眼化及全屏布局 ---
st.markdown("""
    <style>
    /* 彻底移除主区域留白 */
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    header, footer {visibility: hidden;}

    /* 自定义侧边栏把手：亮青色悬浮按钮，确保关闭后依然清晰可见 */
    button[data-testid="sidebar-button"] {
        background-color: #00d4ff !important; 
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        width: 45px !important;
        height: 45px !important;
        left: 0px !important;
        top: 20px !important;
        z-index: 10000 !important; /* 确保层级高于地图 */
        box-shadow: 3px 3px 12px rgba(0,0,0,0.4) !important;
    }
    
    /* 侧边栏背景定制 */
    section[data-testid="stSidebar"] {
        background-color: #111111 !important;
        width: 380px !important;
    }

    /* 修复比例尺溢出：给地图容器增加一个底部内边距，确保控件不贴边 */
    .folium-map {
        margin-bottom: 25px !important;
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
    
    # 账户设置（折叠显示）
    with st.expander("👤 账户设置", expanded=False):
        try:
            default_user = st.secrets["GEONAMES_USER"]
        except:
            default_user = ""
        gn_user = st.text_input("Username", value=default_user, type="password")

    st.markdown("---")
    place_name = st.text_input("输入地名 (拼音/英文)", "zhengzhou")
    
    # 修复语法错误的按钮布局
    col1, col2 = st.columns(2)
    with col1:
        search_btn = st.button("开始查询", use_container_width=True)
    with col2:
        if 'search_results' in st.session_state and st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

# 4. 数据检索逻辑
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] 
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

if search_btn and gn_user:
    s_url = 'http://api.geonames.org/searchJSON'
    try:
        # 参照原始 Python 逻辑进行请求
        s_res = requests.get(s_url, params={'q': place_name, 'username': gn_user, 'maxRows': 15}).json()
        places = s_res.get('geonames', [])
        if places:
            st.session_state.search_results = [
                {
                    "Name": p.get('name'), 
                    "Country": p.get('countryCode'), 
                    "Lat": float(p.get('lat')), 
                    "Lon": float(p.get('lng'))
                } for p in places
            ]
            # 自动跳转到第一个检索结果
            st.session_state.map_center = [st.session_state.search_results[0]['Lat'], st.session_state.search_results[0]['Lon']]
            st.session_state.map_zoom = 11
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"查询出错: {e}")

# 侧边栏：结果列表展示
with st.sidebar:
    if st.session_state.search_results:
        st.markdown("### 搜索结果列表")
        h1, h2, h3 = st.columns([1, 6, 2])
        h1.caption("#")
        h2.caption("地名 (定位)")
        h3.caption("国家")
        
        for i, res in enumerate(st.session_state.search_results):
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.write(f"**{i+1}**")
            if c2.button(f"{res['Name']}", key=f"btn_{i}", use_container_width=True):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 14
                st.rerun()
            c3.write(f"`{res['Country']}`")

# --- 5. 右侧全屏 Folium 地图 ---
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True, # 启用比例尺
    tiles=None
)

# 添加底图
folium.TileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', 
                 attr='CartoDB', name='简约白', show=True).add_to(m)
folium.TileLayer('openstreetmap', name='OSM 标准').add_to(m)
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 attr='Esri卫星', name='Esri 卫星').add_to(m)

# 在地图上添加标记点
for res in st.session_state.search_results:
    folium.Marker([res['Lat'], res['Lon']], tooltip=res['Name']).add_to(m)

# 控件位置微调：将图层控制放在左下角，避开左上角的“拉手”
folium.LayerControl(position='bottomleft').add_to(m)

# 渲染地图：确保 height 足够大以填充视口
st_folium(m, width=2000, height=950, key="main_gis_map")
