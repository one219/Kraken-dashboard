
import streamlit as st
import krakenex
import pandas as pd
from datetime import datetime

api = krakenex.API()
api.load_key('kraken.key')

st.set_page_config(page_title="Kraken Dashboard", layout="centered")

def get_asset_pairs():
    resp = api.query_public('AssetPairs')['result']
    mapping = {}
    for pair, details in resp.items():
        base = details['base']
        quote = details['quote']
        if quote == 'ZUSD':
            mapping[base] = pair
    return mapping

def get_all_balances():
    balances = api.query_private('Balance')['result']
    return {k: float(v) for k, v in balances.items() if float(v) > 0}

def get_live_prices(asset_pairs):
    prices = {}
    ticker = api.query_public('Ticker', {'pair': ','.join(asset_pairs.values())})['result']
    for asset, pair in asset_pairs.items():
        prices[asset] = float(ticker[pair]['c'][0])
    return prices

def get_portfolio_data():
    balances = get_all_balances()
    asset_pairs = get_asset_pairs()
    prices = get_live_prices(asset_pairs)

    data = []
    total_value = 0

    for asset, amount in balances.items():
        price = prices.get(asset, 1 if asset == 'ZUSD' else 0)
        value = amount * price
        total_value += value
        symbol = asset.replace('X', '').replace('Z', '')
        data.append({
            'Asset': symbol,
            'KrakenCode': asset,
            'Balance': amount,
            'Price (USD)': price,
            'Value (USD)': value
        })

    df = pd.DataFrame(data)
    df = df.sort_values(by='Value (USD)', ascending=False)
    return df, total_value, asset_pairs

def place_order(pair, side, volume):
    order = api.query_private('AddOrder', {
        'pair': pair,
        'type': side.lower(),
        'ordertype': 'market',
        'volume': volume
    })
    return order

# --- Streamlit App ---
st.title("💼 Kraken Portfolio Dashboard + Trader")
st.markdown("---")

df, total_value, pair_map = get_portfolio_data()

st.dataframe(df[['Asset', 'Balance', 'Price (USD)', 'Value (USD)']].style.format({
    "Balance": "{:.6f}",
    "Price (USD)": "${:,.2f}",
    "Value (USD)": "${:,.2f}"
}), use_container_width=True)

st.metric("📊 Total Portfolio Value", f"${total_value:,.2f}")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("⚠️ Use caution. Market orders are live and irreversible.")

st.markdown("---")
st.subheader("⚙️ Manual Trade")

with st.form("trade_form"):
    asset_to_trade = st.selectbox("Select Asset to Trade", df['Asset'].tolist())
    trade_type = st.radio("Action", ['Buy', 'Sell'], horizontal=True)
    volume = st.text_input("Volume (in crypto units)", "0.001")

    submitted = st.form_submit_button("Place Trade")

    if submitted:
        kraken_base = df[df['Asset'] == asset_to_trade]['KrakenCode'].values[0]
        kraken_pair = pair_map.get(kraken_base)

        if not kraken_pair:
            st.error("Invalid trading pair.")
        else:
            result = place_order(kraken_pair, trade_type.lower(), volume)
            if 'error' in result and result['error']:
                st.error(f"Order failed: {result['error']}")
            else:
                st.success(f"{trade_type} order placed for {volume} {asset_to_trade}")
