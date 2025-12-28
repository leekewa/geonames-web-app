import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面配置：必须是第一行
st.set_page_config(page_title="GeoNames GIS", layout="wide")

# --- 2. 激进的 CSS：强行填满屏幕并美化左侧 ---
st.markdown("""
    <style>
    /* 移除主内容区域的边距 */
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
        height: 100vh !important;
    }
    /* 隐藏顶部装饰条 */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 调整侧边栏宽度和间距 */
    section[data-testid="stSidebar"] {
        width: 380px !important;
        padding-top: 1rem !important;
    }
    /* 使侧边栏里的按钮看起来像表格行 */
    .stButton > button {
        border-radius: 0px;
        border: 1px solid #333;
        margin-bottom: -1px;
        text-align: left;
        padding: 5px 10px;
        background-color: #1e1e1e;
        color: #ddd;
    }
    .stButton > button:hover {
        background-color: #2e2e2e;
        border-color: #4e4e4e;
    }
    </style>
    """, unsafe_allow_html=True)

# 安全获取用户名
gn_user = st.sidebar.text_input("GeoNames 用户名", 
                                 value=st.secrets.get("GEONAMES_USER", ""), 
                                 type="password")

# 初始化状态
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'map_center' not in st.session_state:
    st.session_state.map_center = [34.7466, 113.6253] # 默认郑州
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5

# --- 3. 左侧控制台 ---
with st.sidebar:
    st.title("🔍 检索控制台")
    place_name = st.text_input("输入目标地名 (拼音/英文)", "zhengzhou")
    
    c1, c2 = st.columns(2)
    with c1:
        search_btn = st.button("开始检索", use_container_width=True)
    with c2:
        if st.session_state.search_results:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", use_container_width=True)

    if search_btn:
        with st.spinner('加载中...'):
            s_url = 'http://api.geonames.org/searchJSON'
            s_res = requests.get(s_url, params={'q': place_name, 'username': gn_user, 'maxRows': 20}).json()
            places = s_res.get('geonames', [])
            if places:
                st.session_state.search_results = [
                    {"Name": p.get('name'), "Country": p.get('countryCode'), "Admin": p.get('adminName1'), 
                     "Lat": float(p.get('lat')), "Lon": float(p.get('lng'))} for p in places
                ]
                st.session_state.map_center = [st.session_state.search_results[0]['Lat'], st.session_state.search_results[0]['Lon']]
                st.session_state.map_zoom = 11

    # 表格态结果列表
    if st.session_state.search_results:
        st.write("---")
        # 模拟表头
        h1, h2, h3 = st.columns([1, 4, 2])
        h1.caption("序号")
        h2.caption("地名 (点击跳转)")
        h3.caption("代码")
        
        for i, res in enumerate(st.session_state.search_results):
            col1, col2, col3 = st.columns([1, 4, 2])
            col1.write(f"`{i+1}`")
            # 使用按钮作为点击单元格
            if col2.button(f"{res['Name']}", key=f"p_{i}", use_container_width=True):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 13
            col3.write(f"`{res['Country']}`")

# --- 4. 右侧全屏地图 ---
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
    tiles=None # 手动添加图层
)

# 底图组
folium.TileLayer('openstreetmap', name='OSM (普通版)').add_to(m)
folium.TileLayer(
    tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attr='&copy; CartoDB', name='CartoDB (简约白)'
).add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Esri (卫星图)'
).add_to(m)

# 标记点
if st.session_state.search_results:
    for res in st.session_state.search_results:
        folium.Marker(
            [res['Lat'], res['Lon']],
            popup=res['Name'],
            tooltip=res['Name']
        ).add_to(m)

# 控件置于左下角
folium.LayerControl(position='bottomleft').add_to(m)

# 关键：st_folium 的 width=1400左右 或填 None 配合 CSS 达到满屏
st_folium(m, width=2000, height=1000, key="full_map")
