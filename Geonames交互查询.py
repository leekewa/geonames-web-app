import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. 页面配置：必须是第一行
st.set_page_config(page_title="GeoNames GIS 控制台", layout="wide")

# 自定义 CSS：美化界面
st.markdown("""
    <style>
    .main .block-container {padding: 0; height: 100vh;}
    section[data-testid="stSidebar"] {width: 400px !important;}
    </style>
    """, unsafe_allow_html=True)

# 2. 安全性：处理用户名
# 优先从部署环境的 Secrets 获取，如果没有则显示输入框
gn_user = st.sidebar.text_input("GeoNames 用户名", 
                                 value=st.secrets.get("GEONAMES_USER", ""), 
                                 type="password",
                                 help="为了安全，建议在 Streamlit Cloud 后台设置 Secrets")

# 初始化 Session State (用于存储搜索结果和选中的点)
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'map_center' not in st.session_state:
    st.session_state.map_center = [20, 0] # 默认初始中心点
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 2

# 3. 左侧控制台 (Sidebar)
with st.sidebar:
    st.title("🔍 检索控制台")
    place_name = st.text_input("输入目标地名 (拼音/英文)", "Beihai")
    
    col1, col2 = st.columns(2)
    with col1:
        search_btn = st.button("开始检索", use_container_width=True)
    with col2:
        if st.session_state.search_results is not None:
            csv = pd.DataFrame(st.session_state.search_results).to_csv(index=False).encode('utf-8')
            st.download_button("导出 CSV", data=csv, file_name=f"{place_name}.csv", mime='text/csv')

    # 逻辑处理：搜索请求
    if search_btn:
        if not gn_user:
            st.error("请输入 GeoNames 用户名！")
        else:
            with st.spinner('检索中...'):
                # 获取邮编
                pc_url = 'http://api.geonames.org/postalCodeSearchJSON'
                pc_res = requests.get(pc_url, params={'placename': place_name, 'maxRows': 1, 'username': gn_user}).json()
                pc_info = pc_res.get('postalCodes', [{}])[0]
                
                # 获取详细点位
                s_url = 'http://api.geonames.org/searchJSON'
                s_res = requests.get(s_url, params={'q': place_name, 'username': gn_user, 'maxRows': 20}).json()
                places = s_res.get('geonames', [])
                
                if places:
                    results = []
                    for p in places:
                        results.append({
                            "Name": p.get('name'),
                            "Country": p.get('countryName'),
                            "Admin": p.get('adminName1'),
                            "Pop": p.get('population', 0),
                            "Lat": float(p.get('lat')),
                            "Lon": float(p.get('lng')),
                            "Postal": pc_info.get('postalCode', 'N/A')
                        })
                    st.session_state.search_results = results
                    # 默认跳转到第一个搜索结果
                    st.session_state.map_center = [results[0]['Lat'], results[0]['Lon']]
                    st.session_state.map_zoom = 10
                else:
                    st.warning("未找到结果")

    # 在控制台显示结果列表
    if st.session_state.search_results:
        st.subheader(f"结果列表 ({len(st.session_state.search_results)})")
        for i, res in enumerate(st.session_state.search_results):
            if st.button(f"📍 {res['Name']}, {res['Country']}", key=f"btn_{i}"):
                st.session_state.map_center = [res['Lat'], res['Lon']]
                st.session_state.map_zoom = 13

# 4. 右侧全屏地图区域
# 创建 Folium 地图对象
m = folium.Map(
    location=st.session_state.map_center, 
    zoom_start=st.session_state.map_zoom,
    control_scale=True
)

# 添加底图
folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
folium.TileLayer(
    tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attr='&copy; CartoDB',
    name='CartoDB简约白'
).add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite'
).add_to(m)

# 添加搜索点位标记
if st.session_state.search_results:
    for res in st.session_state.search_results:
        folium.Marker(
            [res['Lat'], res['Lon']],
            popup=f"<b>{res['Name']}</b><br>Pop: {res['Pop']}<br>Zip: {res['Postal']}",
            tooltip=res['Name']
        ).add_to(m)

# 将图层控制置于左下角 (通过 CSS 或默认)
folium.LayerControl(position='bottomleft').add_to(m)

# 在 Streamlit 中渲染
st_folium(m, width="100%", height=800, key="main_map")
