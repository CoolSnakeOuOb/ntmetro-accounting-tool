import streamlit as st
import pandas as pd
import io

# ==========================================
# 1. 定義共用工具 (路線判斷邏輯)
# ==========================================
def get_route_label(text):
    """
    輸入摘要文字，回傳對應的路線名稱
    """
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
# 2. 定義核心計算邏輯 (通用版)
# ==========================================
def calculate_revenue_by_keyword(df, target_keyword):
    """
    輸入：原始 DataFrame, 目標科目關鍵字 (例如 "廣告收入" 或 "客運收入")
    輸出：整理好的結果 DataFrame, 總金額
    """
    account_col_idx = -1

    # 1. 自動尋找包含該關鍵字的科目在哪一欄
    for col in range(10): # 掃描前 10 欄
        if df.iloc[:, col].astype(str).str.contains(target_keyword).any():
            account_col_idx = col
            break

    if account_col_idx == -1:
        return None, f"❌ 找不到包含「{target_keyword}」的科目，請確認 Excel 內容。"

    # 2. 篩選資料
    mask = df.iloc[:, account_col_idx].astype(str).str.contains(target_keyword)
    revenue_df = df[mask].copy()

    if revenue_df.empty:
        return None, f"⚠️ 找到了科目欄位，但篩選後沒有任何「{target_keyword}」的資料。"

    # 3. 整理欄位 (摘要=F/idx 5, 借方=G/idx 6, 貸方=H/idx 7)
    try:
        revenue_df['摘要'] = revenue_df.iloc[:, 5].astype(str)
        debit = pd.to_numeric(revenue_df.iloc[:, 6], errors='coerce').fillna(0)
        credit = pd.to_numeric(revenue_df.iloc[:, 7], errors='coerce').fillna(0)
        
        # 收入邏輯：淨額 = 貸方 - 借方
        revenue_df['金額'] = credit - debit
    except Exception as e:
        return None, f"❌ 欄位讀取錯誤 (預期 F=摘要, G=借方, H=貸方): {e}"

    # 4. 進行路線分類 (呼叫上面的共用函數)
    revenue_df['歸屬路線'] = revenue_df['摘要'].apply(get_route_label)

    # 5. 彙整統計
    result = revenue_df.groupby('歸屬路線')['金額'].sum()
    
    # 排序
    custom_order = ['淡海輕軌', '安坑輕軌', '環狀線', '三鶯線', '各線分攤']
    result = result.reindex(custom_order).fillna(0)

    total_amount = result.sum()
    
    # 轉回 DataFrame 格式以便顯示
    result_df = result.reset_index()
    col_name = f"{target_keyword}淨額" # 動態命名欄位，例如 "客運收入淨額"
    result_df.columns = ['歸屬路線', col_name]
    
    return result_df, total_amount

# ==========================================
# 3. 建構 Web 介面 (UI層)
# ==========================================
st.set_page_config(page_title="會計執行率分析", page_icon="📊", layout="wide") 
# layout="wide" 讓畫面變寬，比較好閱讀

st.title("📊 會計執行率分析系統")
st.markdown("請上傳日記帳 Excel 檔案，系統將自動分析各項收入指標。")

# 檔案上傳元件
uploaded_file = st.file_uploader("請拖曳或選擇 Excel 檔案", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, header=None)
        st.success("✅ 檔案讀取成功！")
        
        st.divider() # 分隔線

        # 建立分頁籤 (Tabs)
# 1. 在這裡多加一個變數 tab3，並在列表裡多加一個名稱
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["廣告收入", "客運收入", "租賃收入","政府補助收入","什項營業收入"])

        # --- 第一頁：廣告收入 ---
        with tab1:
            st.subheader("廣告收入統計")
            # 呼叫通用函數，傳入 "廣告收入"
            res_ad, total_ad = calculate_revenue_by_keyword(df, "廣告收入")
            
            if res_ad is None:
                st.error(total_ad)
            else:
                col1, col2 = st.columns([1, 2]) # 左邊窄，右邊寬
                with col1:
                    st.metric("廣告收入總計", f"${total_ad:,.0f}")
                with col2:
                    st.dataframe(
                        res_ad.style.format({res_ad.columns[1]: "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

        # --- 第二頁：客運收入 ---
        with tab2:
            st.subheader("客運收入統計")
            # 呼叫通用函數，傳入 "客運收入"
            res_ticket, total_ticket = calculate_revenue_by_keyword(df, "客運收入")
            
            if res_ticket is None:
                st.error(total_ticket)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("客運收入總計", f"${total_ticket:,.0f}")
                with col2:
                    st.dataframe(
                        res_ticket.style.format({res_ticket.columns[1]: "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

        with tab3:
            st.subheader("租賃收入統計")

            res_ticket, total_ticket = calculate_revenue_by_keyword(df, "租賃收入")
            
            if res_ticket is None:
                st.error(total_ticket)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("租賃收入總計", f"${total_ticket:,.0f}")
                with col2:
                    st.dataframe(
                        res_ticket.style.format({res_ticket.columns[1]: "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

        with tab4:
            st.subheader("政府補助收入統計")
            res_ticket, total_ticket = calculate_revenue_by_keyword(df, "政府補助收入")
            
            if res_ticket is None:
                st.error(total_ticket)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("政府補助收入總計", f"${total_ticket:,.0f}")
                with col2:
                    st.dataframe(
                        res_ticket.style.format({res_ticket.columns[1]: "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

        with tab5:
            st.subheader("什項營業統計")
            res_ticket, total_ticket = calculate_revenue_by_keyword(df, "什項營業收入")
            
            if res_ticket is None:
                st.error(total_ticket)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("什項營業總計收入", f"${total_ticket:,.0f}")
                with col2:
                    st.dataframe(
                        res_ticket.style.format({res_ticket.columns[1]: "{:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )
        
        

        

    except Exception as e:
        st.error(f"讀取檔案時發生未預期的錯誤：{e}")

else:
    st.info("👆 請先在上方上傳檔案")