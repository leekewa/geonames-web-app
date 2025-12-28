import streamlit as st
import requests
import pandas as pd

# 页面配置
st.set_page_config(page_title="GeoNames 地名查询工具", layout="wide")

st.title("🌍 GeoNames 地名综合查询")
st.write("输入地名，获取邮编、人口、经纬度及行政区划信息。")

# 侧边栏配置
username = st.sidebar.text_input("GeoNames 用户名", value="leekewa")
place_name = st.text_input("请输入查询地名 (例如: Beihai)", "Beihai")

if st.button("开始查询"):
    with st.spinner('正在检索数据...'):
        # 1. 邮政编码搜索
        postal_code_url = 'http://api.geonames.org/postalCodeSearchJSON'
        pc_params = {'placename': place_name, 'maxRows': 1, 'username': username}
        
        try:
            pc_res = requests.get(postal_code_url, params=pc_params).json()
            postal_code_info = pc_res.get('postalCodes', [None])[0]
            
            # 2. 地理详细搜索
            search_url = 'http://api.geonames.org/searchJSON'
            s_params = {'q': place_name, 'username': username, 'maxRows': 10}
            s_res = requests.get(search_url, params=s_params).json()
            places = s_res.get('geonames', [])

            if places:
                # 构建数据列表（对应你原代码的 tabledata）
                data_list = []
                for place in places:
                    row = {
                        'geonameId': place.get('geonameId'),
                        'Name': place.get('name'),
                        'Postal Code': postal_code_info.get('postalCode') if postal_code_info else 'N/A',
                        'Population': place.get('population') if place.get('population') != 0 else '/',
                        'Country': place.get('countryName'),
                        'Admin Name 1': place.get('adminName1'),
                        'Admin Name 2': postal_code_info.get('adminName2', '--') if postal_code_info else '--',
                        'Latitude': place.get('lat'),
                        'Longitude': place.get('lng'),
                        'Feature Code': place.get('fcode')
                    }
                    data_list.append(row)

                # 使用 Pandas 转换为表格，并在网页展示
                df = pd.DataFrame(data_list)
                st.success(f"找到 {len(places)} 条结果")
                
                # 网页展示表格
                st.dataframe(df, use_container_width=True)
                
                # 额外功能：在地图上打点
                map_data = df[['Latitude', 'Longitude']].astype(float)
                map_data.columns = ['lat', 'lon']
                st.map(map_data)
                
            else:
                st.warning("未找到相关地名。")
                
        except Exception as e:
            st.error(f"发生错误: {e}")