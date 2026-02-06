import streamlit as st
import pandas as pd
import io

# ==========================================
# 1. 定義共用工具 (路線判斷邏輯)
# ==========================================
def get_route_label(text):
    text = str(text).strip()
    if '淡海' in text:
        return '淡海輕軌'
    if '安坑' in text:
        return '安坑輕軌'
    if '環狀' in text:
        return '環狀線'
    if '三鶯' in text:
        return '三鶯線'
    return '各線分攤'

# ==========================================
# 2. 定義核心計算邏輯 (含客運收入特殊平攤規則)
# ==========================================
def calculate_revenue_by_keyword(df, target_keyword):
    """
    輸入：原始 DataFrame, 目標科目關鍵字
    輸出：結果 DataFrame, 總金額, 原始明細(debug用)
    """
    account_col_idx = -1

    # 1. 自動尋找科目欄位
    for col in range(10): 
        if df.iloc[:, col].astype(str).str.contains(target_keyword).any():
            account_col_idx = col
            break

    if account_col_idx == -1:
        return None, f"❌ 找不到「{target_keyword}」科目", None

    # 2. 篩選資料
    mask = df.iloc[:, account_col_idx].astype(str).str.contains(target_keyword)
    revenue_df = df[mask].copy()

    if revenue_df.empty:
        return None, f"⚠️ 沒資料：{target_keyword}", None

    # 3. 整理欄位
    try:
        # 抓取部門與摘要來判斷路線
        text_col_c = revenue_df.iloc[:, 2].astype(str).fillna('')
        text_col_d = revenue_df.iloc[:, 3].astype(str).fillna('')
        text_col_f = revenue_df.iloc[:, 5].astype(str).fillna('') 
        
        revenue_df['全部分類資訊'] = text_col_c + " " + text_col_d + " " + text_col_f
        revenue_df['摘要'] = text_col_f # 顯示用摘要維持乾淨
        
        # 原始數據
        revenue_df['原始借方'] = revenue_df.iloc[:, 6]
        revenue_df['原始貸方'] = revenue_df.iloc[:, 7]

        # 轉數字
        debit = pd.to_numeric(revenue_df.iloc[:, 6], errors='coerce').fillna(0)
        credit = pd.to_numeric(revenue_df.iloc[:, 7], errors='coerce').fillna(0)
        
        revenue_df['借方'] = debit
        revenue_df['貸方'] = credit
        revenue_df['金額'] = credit - debit

    except Exception as e:
        return None, f"❌ 欄位讀取錯誤: {e}", None

    # 4. 初步路線分類
    revenue_df['歸屬路線'] = revenue_df['全部分類資訊'].apply(get_route_label)

    # ★★★ 新增邏輯：客運收入若未分類，則平攤給淡海/安坑 ★★★
    if target_keyword == "客運收入":
        split_mask = revenue_df['歸屬路線'] == '各線分攤'
        
        if split_mask.any():
            rows_to_split = revenue_df[split_mask].copy()
            revenue_df = revenue_df[~split_mask]
            
            # 淡海 50%
            dh_part = rows_to_split.copy()
            dh_part['歸屬路線'] = '淡海輕軌'
            dh_part['金額'] = dh_part['金額'] / 2
            dh_part['借方'] = dh_part['借方'] / 2
            dh_part['貸方'] = dh_part['貸方'] / 2
            dh_part['摘要'] = dh_part['摘要'] + ' (分攤-淡海)'
            
            # 安坑 50%
            ak_part = rows_to_split.copy()
            ak_part['歸屬路線'] = '安坑輕軌'
            ak_part['金額'] = ak_part['金額'] / 2
            ak_part['借方'] = ak_part['借方'] / 2
            ak_part['貸方'] = ak_part['貸方'] / 2
            ak_part['摘要'] = ak_part['摘要'] + ' (分攤-安坑)'
            
            revenue_df = pd.concat([revenue_df, dh_part, ak_part], ignore_index=True)

    # 5. 統計結果
    result = revenue_df.groupby('歸屬路線')['金額'].sum()
    custom_order = ['淡海輕軌', '安坑輕軌', '環狀線', '三鶯線', '各線分攤']
    result = result.reindex(custom_order).fillna(0)
    total_amount = result.sum()
    
    result_df = result.reset_index()
    result_df.columns = ['歸屬路線', f'{target_keyword}淨額']
    
    return result_df, total_amount, revenue_df

# ==========================================
# 3. 建構 Web 介面 (UI層)
# ==========================================
st.set_page_config(page_title="會計執行率分析", page_icon="📊", layout="wide") 

st.title("📊 會計執行率分析系統")
st.markdown("請上傳日記帳 Excel 檔案，系統將自動分析各項收入指標。")

# 檔案上傳元件
uploaded_file = st.file_uploader("請拖曳或選擇 Excel 檔案", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=None)
        st.success("✅ 檔案讀取成功！")
        
        st.divider()

        # 建立分頁籤
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["廣告收入", "客運收入", "租賃收入","政府補助收入","什項營業收入"])

        # --- 第一頁：廣告收入 (含細項分析) ---
        with tab1:
            st.subheader("廣告收入統計")
            # 1. 先取得原始資料 (raw_ad_df)
            res_ad, total_ad, raw_ad_df = calculate_revenue_by_keyword(df, "廣告收入")
            
            if res_ad is None:
                st.error(total_ad)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("廣告收入總計", f"${total_ad:,.0f}")
                
                with col2:
                    # ★★★ 新增：廣告細項分類邏輯 ★★★
                    def classify_ad_type(text):
                        if "墩柱" in text:
                            return "墩柱廣告收入"
                        if "外牆" in text:
                            return "外牆廣告收入"
                        # 預設歸類為車站車廂 (因為最常見)
                        return "車站車廂廣告收入"
                    
                    # 應用分類邏輯
                    raw_ad_df['細項名稱'] = raw_ad_df['摘要'].apply(classify_ad_type)
                    
                    # 製作細項統計表 (群組: 細項 + 路線)
                    detailed_ad = raw_ad_df.groupby(['細項名稱', '歸屬路線'])['金額'].sum().reset_index()
                    
                    # 排序美化
                    detailed_ad = detailed_ad.sort_values(by=['細項名稱', '歸屬路線'])
                    detailed_ad.columns = ['項目', '路線', '金額']

                    # 顯示表格
                    st.markdown("##### 📋 各細項分路報表")
                    st.dataframe(
                        detailed_ad.style.format({"金額": "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 顯示原始匯總 (如果您還想保留原本的簡單版，可以留著，不想看可以註解掉)
                    with st.expander("查看路線匯總 (簡單版)"):
                        st.dataframe(res_ad.style.format({res_ad.columns[1]: "{:,.0f}"}), use_container_width=True, hide_index=True)

        # --- 第二頁：客運收入 ---
        with tab2:
            st.subheader("客運收入統計")
            res_ticket, total_ticket, _ = calculate_revenue_by_keyword(df, "客運收入")
            
            if res_ticket is None:
                st.error(total_ticket)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("客運收入總計", f"${total_ticket:,.0f}")
                with col2:
                    st.dataframe(res_ticket.style.format({res_ticket.columns[1]: "{:,.0f}"}), use_container_width=True, hide_index=True)

        # --- 第三頁：租賃收入 ---
        with tab3:
            st.subheader("租賃收入統計")
            res_rent, total_rent, _ = calculate_revenue_by_keyword(df, "租賃收入")
            
            if res_rent is None:
                st.error(total_rent)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("租賃收入總計", f"${total_rent:,.0f}")
                with col2:
                    st.dataframe(res_rent.style.format({res_rent.columns[1]: "{:,.0f}"}), use_container_width=True, hide_index=True)

        # --- 第四頁：政府補助收入 ---
        with tab4:
            st.subheader("政府補助收入統計")
            res_gov, total_gov, _ = calculate_revenue_by_keyword(df, "政府補助收入")
            
            if res_gov is None:
                st.error(total_gov)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("政府補助收入總計", f"${total_gov:,.0f}")
                with col2:
                    st.dataframe(res_gov.style.format({res_gov.columns[1]: "{:,.0f}"}), use_container_width=True, hide_index=True)

        # --- 第五頁：什項營業收入 ---
        with tab5:
            st.subheader("什項營業統計")
            res_misc, total_misc, _ = calculate_revenue_by_keyword(df, "什項營業收入")
            
            if res_misc is None:
                st.error(total_misc)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("什項營業總計收入", f"${total_misc:,.0f}")
                with col2:
                    st.dataframe(res_misc.style.format({res_misc.columns[1]: "{:,.0f}"}), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"讀取檔案時發生未預期的錯誤：{e}")

else:
    st.info("👆 請先在上方上傳檔案")