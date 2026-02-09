"""
Gooaye Radar — Streamlit 前端 Dashboard
透過 Backend API 顯示追蹤股票、技術指標與觀點版控。
"""

import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# ---------------------------------------------------------------------------
# 頁面設定
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="股癌投資雷達 Gooaye Radar",
    page_icon="📡",
    layout="wide",
)

st.title("📡 股癌投資雷達 Gooaye Radar")
st.caption("V2.0 — 三層漏斗 + 籌碼面訊號")


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict | list | None:
    """GET 請求 Backend API。"""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_post(path: str, json_data: dict) -> dict | None:
    """POST 請求 Backend API。"""
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=json_data, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_patch(path: str, json_data: dict) -> dict | None:
    """PATCH 請求 Backend API。"""
    try:
        resp = requests.patch(f"{BACKEND_URL}{path}", json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


@st.cache_data(ttl=300, show_spinner="載入股票資料中...")
def fetch_stocks() -> list | None:
    """取得所有追蹤股票（含技術指標），結果快取 5 分鐘。"""
    return api_get("/stocks")


@st.cache_data(ttl=300, show_spinner="載入已移除股票...")
def fetch_removed_stocks() -> list | None:
    """取得已移除股票清單，結果快取 5 分鐘。"""
    return api_get("/stocks/removed")


# ---------------------------------------------------------------------------
# Sidebar: 新增股票 & 掃描
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🛠️ 操作面板")

    # -- 新增股票 --
    st.subheader("➕ 新增追蹤股票")
    with st.form("add_stock_form", clear_on_submit=True):
        new_ticker = st.text_input("股票代號", placeholder="例如 AAPL, TSM, NVDA")
        new_category = st.selectbox(
            "分類",
            options=["Trend_Setter", "Moat", "Growth"],
            format_func=lambda x: {
                "Trend_Setter": "🌊 風向球 (Trend Setter)",
                "Moat": "🏰 護城河 (Moat)",
                "Growth": "🚀 成長夢想 (Growth)",
            }.get(x, x),
        )
        new_thesis = st.text_area("初始觀點", placeholder="寫下你對這檔股票的看法...")
        submitted = st.form_submit_button("新增")

        if submitted:
            if not new_ticker.strip():
                st.warning("⚠️ 請輸入股票代號。")
            elif not new_thesis.strip():
                st.warning("⚠️ 請輸入初始觀點。")
            else:
                result = api_post("/ticker", {
                    "ticker": new_ticker.strip().upper(),
                    "category": new_category,
                    "thesis": new_thesis.strip(),
                })
                if result:
                    st.success(f"✅ 已新增 {new_ticker.upper()} 到追蹤清單！")
                    st.rerun()

    st.divider()

    # -- 全域掃描 (V2 三層漏斗) --
    st.subheader("🔍 三層漏斗掃描")
    if st.button("🚀 執行掃描", use_container_width=True):
        with st.spinner("三層漏斗掃描中，請稍候..."):
            scan_response = api_post("/scan", {})
        if scan_response:
            # 顯示整體市場情緒
            ms = scan_response.get("market_status", {})
            ms_status = ms.get("status", "POSITIVE")
            ms_details = ms.get("details", "")
            ms_pct = ms.get("below_60ma_pct", 0)

            if ms_status == "CAUTION":
                st.error(f"🔴 市場情緒：CAUTION（{ms_pct}% 跌破 60MA）")
            else:
                st.success(f"🟢 市場情緒：POSITIVE（{ms_pct}% 跌破 60MA）")
            st.caption(ms_details)

            st.divider()

            # 逐股掃描結果 — signal badges
            results = scan_response.get("results", [])
            non_normal = [r for r in results if r.get("signal") != "NORMAL"]

            if non_normal:
                st.markdown(f"**發現 {len(non_normal)} 檔異常股票：**")
                for r in non_normal:
                    sig = r.get("signal", "NORMAL")
                    tkr = r.get("ticker", "?")
                    alerts = r.get("alerts", [])

                    if sig == "THESIS_BROKEN":
                        st.error(f"🔴 **THESIS_BROKEN** — {tkr}")
                    elif sig == "CONTRARIAN_BUY":
                        st.success(f"🟢 **CONTRARIAN_BUY** — {tkr}")
                    elif sig == "OVERHEATED":
                        st.warning(f"🟠 **OVERHEATED** — {tkr}")

                    for a in alerts:
                        st.caption(f"  {a}")
            else:
                st.success("✅ 掃描完成，所有股票狀態正常。")

            # 顯示所有 NORMAL 股票的簡要列表
            normal_stocks = [r for r in results if r.get("signal") == "NORMAL"]
            if normal_stocks:
                with st.expander(f"⚪ NORMAL 股票（{len(normal_stocks)} 檔）", expanded=False):
                    for r in normal_stocks:
                        st.info(f"⚪ **NORMAL** — {r.get('ticker', '?')}")

    st.divider()

    # -- 重新整理資料 --
    st.subheader("🔄 資料快取")
    st.caption("股票資料每 5 分鐘自動更新。點擊下方按鈕可立即刷新。")
    if st.button("🔄 立即刷新資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Main Dashboard: 股票清單 (Tabs)
# ---------------------------------------------------------------------------

stocks_data = fetch_stocks()
removed_data = fetch_removed_stocks()

if stocks_data is None:
    st.info("⏳ 無法連線至後端服務，請確認 Backend 是否啟動。")
    st.stop()

# 依分類分組
category_map = {
    "Trend_Setter": [],
    "Moat": [],
    "Growth": [],
}
for stock in (stocks_data or []):
    cat = stock.get("category", "Growth")
    if cat in category_map:
        category_map[cat].append(stock)

removed_list = removed_data or []

tab_trend, tab_moat, tab_growth, tab_archive = st.tabs([
    f"🌊 風向球 ({len(category_map['Trend_Setter'])})",
    f"🏰 護城河 ({len(category_map['Moat'])})",
    f"🚀 成長夢想 ({len(category_map['Growth'])})",
    f"📦 已移除 ({len(removed_list)})",
])


def render_stock_card(stock: dict) -> None:
    """渲染單一股票卡片，包含技術指標與觀點編輯。"""
    ticker = stock["ticker"]
    signals = stock.get("signals") or {}

    with st.container(border=True):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader(f"📊 {ticker}")
            st.caption(f"分類：{stock['category']}")

            if "error" in signals:
                st.warning(signals["error"])
            else:
                price = signals.get("price", "N/A")
                rsi = signals.get("rsi", "N/A")
                ma200 = signals.get("ma200", "N/A")
                ma60 = signals.get("ma60", "N/A")
                bias = signals.get("bias")
                volume_ratio = signals.get("volume_ratio")

                metrics_col1, metrics_col2 = st.columns(2)
                with metrics_col1:
                    st.metric("現價", f"${price}")
                    st.metric("RSI(14)", rsi)
                with metrics_col2:
                    st.metric("200MA", f"${ma200}" if ma200 else "N/A")
                    st.metric("60MA", f"${ma60}" if ma60 else "N/A")

                # 籌碼面指標
                chip_col1, chip_col2 = st.columns(2)
                with chip_col1:
                    if bias is not None:
                        bias_color = "🔴" if bias > 20 else ("🟢" if bias < -20 else "⚪")
                        st.metric(f"{bias_color} 乖離率 Bias", f"{bias}%")
                    else:
                        st.metric("乖離率 Bias", "N/A")
                with chip_col2:
                    if volume_ratio is not None:
                        st.metric("量比 Vol Ratio", f"{volume_ratio}x")
                    else:
                        st.metric("量比 Vol Ratio", "N/A")

                # WhaleWisdom fallback
                institutional = signals.get("institutional")
                if institutional and "N/A failed to get new data" in str(institutional):
                    st.caption(f"⚠️ {institutional}")
                    st.link_button(
                        f"🐋 WhaleWisdom 查詢 {ticker}",
                        f"https://whalewisdom.com/stock/{ticker.lower()}",
                    )

                # 狀態列表
                for s in signals.get("status", []):
                    st.write(s)

        with col2:
            st.markdown("**💡 當前觀點：**")
            st.info(stock.get("current_thesis", "尚無觀點"))

            # -- 觀點歷史與編輯 --
            with st.expander(f"📝 觀點版控 — {ticker}", expanded=False):
                # 取得歷史紀錄
                history = api_get(f"/ticker/{ticker}/thesis")

                if history:
                    st.markdown("**📜 歷史觀點紀錄：**")
                    for entry in history:
                        ver = entry.get("version", "?")
                        content = entry.get("content", "")
                        created = entry.get("created_at", "")
                        st.markdown(
                            f"**v{ver}** ({created[:10] if created else '未知日期'})"
                        )
                        st.text(content)
                        st.divider()
                else:
                    st.caption("尚無歷史觀點紀錄。")

                # 新增觀點
                st.markdown("**✏️ 新增觀點：**")
                new_thesis_content = st.text_area(
                    "觀點內容",
                    key=f"thesis_input_{ticker}",
                    placeholder="寫下你對這檔股票的最新看法...",
                    label_visibility="collapsed",
                )
                if st.button("更新觀點", key=f"thesis_btn_{ticker}"):
                    if new_thesis_content.strip():
                        result = api_post(
                            f"/ticker/{ticker}/thesis",
                            {"content": new_thesis_content.strip()},
                        )
                        if result:
                            st.success(result.get("message", "✅ 觀點已更新"))
                            st.rerun()
                    else:
                        st.warning("⚠️ 請輸入觀點內容。")

            # -- 切換分類 --
            with st.expander(f"🔄 切換分類 — {ticker}", expanded=False):
                current_cat = stock.get("category", "Growth")
                all_categories = ["Trend_Setter", "Moat", "Growth"]
                other_categories = [c for c in all_categories if c != current_cat]

                cat_labels = {
                    "Trend_Setter": "🌊 風向球 (Trend Setter)",
                    "Moat": "🏰 護城河 (Moat)",
                    "Growth": "🚀 成長夢想 (Growth)",
                }
                current_label = cat_labels.get(current_cat, current_cat)
                st.caption(f"目前分類：**{current_label}**")

                new_cat = st.selectbox(
                    "新分類",
                    options=other_categories,
                    format_func=lambda x: cat_labels.get(x, x),
                    key=f"cat_select_{ticker}",
                    label_visibility="collapsed",
                )
                if st.button("確認切換", key=f"cat_btn_{ticker}"):
                    result = api_patch(
                        f"/ticker/{ticker}/category",
                        {"category": new_cat},
                    )
                    if result:
                        st.success(result.get("message", "✅ 分類已切換"))
                        st.cache_data.clear()
                        st.rerun()

            # -- 移除追蹤 --
            with st.expander(f"🗑️ 移除追蹤 — {ticker}", expanded=False):
                st.warning("⚠️ 移除後股票將移至「已移除」分頁，可隨時查閱歷史紀錄。")
                removal_reason = st.text_area(
                    "移除原因",
                    key=f"removal_input_{ticker}",
                    placeholder="寫下你移除這檔股票的原因...",
                    label_visibility="collapsed",
                )
                if st.button("確認移除", key=f"removal_btn_{ticker}", type="primary"):
                    if removal_reason.strip():
                        result = api_post(
                            f"/ticker/{ticker}/deactivate",
                            {"reason": removal_reason.strip()},
                        )
                        if result:
                            st.success(result.get("message", "✅ 已移除"))
                            st.rerun()
                    else:
                        st.warning("⚠️ 請輸入移除原因。")


# -- 渲染各 Tab --
with tab_trend:
    if category_map["Trend_Setter"]:
        for stock in category_map["Trend_Setter"]:
            render_stock_card(stock)
    else:
        st.info("📭 尚無風向球類股票，請在左側面板新增。")

with tab_moat:
    if category_map["Moat"]:
        for stock in category_map["Moat"]:
            render_stock_card(stock)
    else:
        st.info("📭 尚無護城河類股票，請在左側面板新增。")

with tab_growth:
    if category_map["Growth"]:
        for stock in category_map["Growth"]:
            render_stock_card(stock)
    else:
        st.info("📭 尚無成長夢想類股票，請在左側面板新增。")

with tab_archive:
    if removed_list:
        for removed in removed_list:
            ticker = removed["ticker"]
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.subheader(f"📦 {ticker}")
                    category_label = {
                        "Trend_Setter": "🌊 風向球",
                        "Moat": "🏰 護城河",
                        "Growth": "🚀 成長夢想",
                    }.get(removed.get("category", ""), removed.get("category", ""))
                    st.caption(f"分類：{category_label}")
                    removed_at = removed.get("removed_at", "")
                    st.caption(f"移除日期：{removed_at[:10] if removed_at else '未知'}")

                with col2:
                    st.markdown("**🗑️ 移除原因：**")
                    st.error(removed.get("removal_reason", "未知"))

                    st.markdown("**💡 最後觀點：**")
                    st.info(removed.get("current_thesis", "尚無觀點"))

                    # -- 移除歷史 --
                    with st.expander(f"📜 移除歷史 — {ticker}", expanded=False):
                        removals = api_get(f"/ticker/{ticker}/removals")
                        if removals:
                            for entry in removals:
                                created = entry.get("created_at", "")
                                st.markdown(
                                    f"**{created[:10] if created else '未知日期'}**"
                                )
                                st.text(entry.get("reason", ""))
                                st.divider()
                        else:
                            st.caption("尚無移除歷史紀錄。")

                    # -- 觀點歷史 --
                    with st.expander(f"📝 觀點歷史 — {ticker}", expanded=False):
                        history = api_get(f"/ticker/{ticker}/thesis")
                        if history:
                            for entry in history:
                                ver = entry.get("version", "?")
                                content = entry.get("content", "")
                                created = entry.get("created_at", "")
                                st.markdown(
                                    f"**v{ver}** ({created[:10] if created else '未知日期'})"
                                )
                                st.text(content)
                                st.divider()
                        else:
                            st.caption("尚無歷史觀點紀錄。")
    else:
        st.info("📭 目前沒有已移除的股票。")
