import streamlit as st
import pandas as pd
import io

# ==========================================
# 1. 定義核心計算邏輯 (邏輯層)
# ==========================================
def calculate_advertising_revenue(df):
    """
    輸入：原始的 DataFrame (header=None)
    輸出：整理好的結果 DataFrame, 總金額
    """
    target_account = "廣告收入"
    account_col_idx = -1

    # 1. 自動尋找「廣告收入」在哪一欄
    for col in range(10): # 掃描前 10 欄
        # 轉字串並檢查是否包含關鍵字
        if df.iloc[:, col].astype(str).str.contains(target_account).any():
            account_col_idx = col
            break

    if account_col_idx == -1:
        return None, "❌ 找不到「廣告收入」科目，請確認 Excel 內容。"

    # 2. 篩選資料
    mask = df.iloc[:, account_col_idx].astype(str).str.contains(target_account)
    revenue_df = df[mask].copy()

    if revenue_df.empty:
        return None, "⚠️ 找到了科目欄位，但篩選後沒有任何「廣告收入」的資料。"

    # 3. 整理欄位 (摘要=F/idx 5, 借方=G/idx 6, 貸方=H/idx 7)
    try:
        revenue_df['摘要'] = revenue_df.iloc[:, 5].astype(str)
        debit = pd.to_numeric(revenue_df.iloc[:, 6], errors='coerce').fillna(0)
        credit = pd.to_numeric(revenue_df.iloc[:, 7], errors='coerce').fillna(0)
        
        # 收入邏輯：淨額 = 貸方 - 借方
        revenue_df['金額'] = credit - debit
    except Exception as e:
        return None, f"❌ 欄位讀取錯誤 (預期 F=摘要, G=借方, H=貸方): {e}"

    # 4. 路線分類函數
    def get_route_label(text):
        text = str(text).strip()
        if any(k in text for k in ['淡海', '綠山', '藍海']):
            return '淡海輕軌'
        if '安坑' in text:
            return '安坑輕軌'
        if '環狀' in text:
            return '環狀線'
        if '三鶯' in text:
            return '三鶯線'
        return '各線分攤'

    revenue_df['歸屬路線'] = revenue_df['摘要'].apply(get_route_label)

    # 5. 彙整統計
    result = revenue_df.groupby('歸屬路線')['金額'].sum()
    
    # 排序
    custom_order = ['淡海輕軌', '安坑輕軌', '環狀線', '三鶯線', '各線分攤']
    result = result.reindex(custom_order).fillna(0)

    total_amount = result.sum()
    
    # 為了顯示漂亮，把 Series 轉回 DataFrame 並重設 index
    result_df = result.reset_index()
    result_df.columns = ['歸屬路線', '廣告淨收入']
    
    return result_df, total_amount

# ==========================================
# 2. 建構 Web 介面 (UI層)
# ==========================================
st.set_page_config(page_title="會計執行率分析", page_icon="📊")

st.title("📊 會計執行率分析")
st.markdown("請上傳日記帳 Excel 檔案，系統將自動計算 **廣告收入** 分路統計。")

# 檔案上傳元件
uploaded_file = st.file_uploader("請拖曳或選擇 Excel 檔案", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # 讀取檔案 (使用 header=None 以處理不規則標題)
        # 用 st.cache_data 加速重複運算 (選用)
        df = pd.read_excel(uploaded_file, header=None)
        
        st.success("✅ 檔案讀取成功！開始分析...")
        
        # --- 呼叫計算邏輯 ---
        result_df, total_or_msg = calculate_advertising_revenue(df)
        
        # --- 判斷結果 ---
        if result_df is None:
            # 如果回傳 None，代表有錯誤訊息
            st.error(total_or_msg)
        else:
            # 顯示總金額 (大字體指標)
            st.metric(label="本月總廣告淨收入", value=f"${total_or_msg:,.0f}")
            
            # 顯示表格
            st.subheader("📍 各路線收入明細")
            
            # 格式化顯示 (讓千分位逗號出現，但保留數字型態供排序)
            st.dataframe(
                result_df.style.format({"廣告淨收入": "{:,.0f}"}),
                use_container_width=True, # 填滿寬度
                hide_index=True           # 隱藏前面的 0,1,2,3 索引
            )

            # (選用) 讓使用者下載結果
            # csv = result_df.to_csv(index=False).encode('utf-8-sig')
            # st.download_button("📥 下載統計結果 (CSV)", csv, "廣告收入統計.csv")

    except Exception as e:
        st.error(f"讀取檔案時發生未預期的錯誤：{e}")

else:
    st.info("👆 請先在上方上傳檔案")