import csv
import time
import requests
from datetime import datetime, timezone
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

API_URL = "https://explorer-api.veil-project.com/api/Block"
CSV_FILE = "miner_data.csv"
PROOF_TYPE_NAMES = {2: "ProgPoW", 3: "RandomX", 4: "SHA256D"}

# ----------- Data Fetching -----------
def fetch_block(height):
    try:
        response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json={"height": height, "offset": 0, "count": 1})
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"Error fetching block {height}: {e}")
    return None

def fetch_blockchain_info():
    try:
        response = requests.get("https://explorer-api.veil-project.com/api/BlockchainInfo")
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"Error fetching blockchain info: {e}")
    return None

def parse_block_data(block_data):
    height = block_data["block"]["height"]
    timestamp = block_data["block"]["time"]
    proof_type = block_data["block"].get("proof_type", -1)
    difficulty = block_data["block"].get("difficulty", 0)
    txs = block_data.get("transactions", [])

    algo = "Stake"
    address = "Unknown"

    if proof_type in [2, 3, 4]:
        algo = PROOF_TYPE_NAMES.get(proof_type, "Unknown")
        if txs and "outputs" in txs[0]:
            for output in txs[0]["outputs"]:
                if output.get("isCoinBase") and output.get("addresses"):
                    address = output["addresses"][0]
                    break

    return (
        height,
        datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        address,
        algo,
        difficulty
    )

def append_to_csv(height, timestamp, address, algo, difficulty):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Block Height", "Timestamp", "Address", "Algorithm", "Difficulty"])
        writer.writerow([height, timestamp, address, algo, difficulty])

def get_existing_heights():
    if not os.path.exists(CSV_FILE):
        return set()
    df = pd.read_csv(CSV_FILE)
    return set(df["Block Height"].astype(int))

def get_estimated_randomx_hashrate():
    try:
        stats = requests.get("https://explorer-api.veil-project.com/api/getchainalgostats").json()
        total_blocks = stats.get("period", 0)
        randomx_blocks = stats.get("randomx", 0)

        if randomx_blocks == 0 or total_blocks == 0:
            return 0

        seconds = stats.get("finish", 0) - stats.get("start", 0)
        avg_block_time = seconds / total_blocks
        avg_rx_spacing = avg_block_time * (total_blocks / randomx_blocks)

        difficulty = requests.get("https://explorer-api.veil-project.com/api/BlockchainInfo").json().get("chainInfo", {}).get("difficulty_randomx", 0)
        if difficulty > 0 and avg_rx_spacing > 0:
            return difficulty * 2**32 / avg_rx_spacing
        return 0
    except Exception as e:
        print(f"[RandomX Estimation Error] {e}")
        return 0

def format_hashrate(hr, algo):
    if algo == "progpow":
        return f"{hr / 1_000_000:,.2f} MH/s"
    elif algo == "sha256d":
        return f"{hr:,.2f} H/s"
    elif algo == "randomx":
        return f"{hr / 1_000:,.2f} kH/s"
    return f"{hr:,.2f} H/s"

def get_colored_arrow(current, previous):
    if current > previous:
        return ":green[↑]"
    elif current < previous:
        return ":red[↓]"
    return ":gray[→]"

# ----------- Streamlit Dashboard -----------
st.set_page_config(page_title="Veil Miner Dashboard", layout="wide")
st.title("⛏️ Veil Miner Dashboard")

# Manual refresh button
if st.button("🔄 Refresh now"):
    st.rerun()

# Auto refresh every 5 min
FULL_REFRESH_INTERVAL = 5 * 60
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = time.time()
if time.time() - st.session_state["last_refresh_time"] >= FULL_REFRESH_INTERVAL:
    st.session_state["last_refresh_time"] = time.time()
    st.rerun()

info = fetch_blockchain_info()
if not info or "currentSyncedBlock" not in info or "chainInfo" not in info or "bestblockhash" not in info["chainInfo"]:
    st.error("[-] Failed to fetch BlockchainInfo. The explorer may be down.")
    st.stop()

latest_height = info["currentSyncedBlock"]
start_height = max(0, latest_height - 60)
existing_heights = get_existing_heights()
latest_hash = info["chainInfo"]["bestblockhash"]

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    df = pd.DataFrame(columns=["Block Height", "Timestamp", "Address", "Algorithm", "Difficulty"])

new_blocks_added = 0
try:
    for height in range(start_height, latest_height + 1):
        if height in existing_heights:
            continue
        data = fetch_block(height)
        if data and "block" in data:
            parsed = parse_block_data(data)
            append_to_csv(*parsed)
            new_blocks_added += 1
    df = pd.read_csv(CSV_FILE)
except Exception as e:
    st.error(f"Error during block refresh: {e}")

st.markdown(f"### 📦 Current Block Height: `{latest_height}`")
st.markdown(f"### 🔗 Best Block Hash: `{latest_hash}`")
st.markdown(f"### Displaying `{len(df)}` Mined Blocks")

# Difficulty Stats
st.subheader("📊 Difficulty")
diffs = {
    "ProgPoW": info["chainInfo"].get("difficulty_progpow", 0),
    "RandomX": info["chainInfo"].get("difficulty_randomx", 0),
    "SHA256D": info["chainInfo"].get("difficulty_sha256d", 0),
    "PoS": info["chainInfo"].get("difficulty_pos", 0)
}
trend_df = df[df["Algorithm"].isin(["ProgPoW", "RandomX", "SHA256D"])].sort_values("Block Height", ascending=False)
prev_diffs = {}
for algo in ["ProgPoW", "RandomX", "SHA256D"]:
    vals = trend_df[trend_df["Algorithm"] == algo]["Difficulty"].values
    prev_diffs[algo] = vals[1] if len(vals) >= 2 else diffs[algo]

cols = st.columns(4)
for i, algo in enumerate(["ProgPoW", "RandomX", "SHA256D", "PoS"]):
    arrow = get_colored_arrow(diffs[algo], prev_diffs.get(algo, diffs[algo])) if algo != "PoS" else ""
    cols[i].markdown(f"**{algo} Difficulty:** `{diffs[algo]:.5f}` {arrow}")

# Hashrates
st.subheader("⚙️ Estimated Network Hashrate")
progpow_hr = info["networkHashrates"].get("progpow", 0)
sha256d_hr = info["networkHashrates"].get("sha256d", 0)
randomx_hr = get_estimated_randomx_hashrate()
hr_cols = st.columns(3)
hr_cols[0].metric("ProgPoW", format_hashrate(progpow_hr, "progpow"))
hr_cols[1].metric("RandomX", format_hashrate(randomx_hr, "randomx"))
hr_cols[2].metric("SHA256D", format_hashrate(sha256d_hr, "sha256d"))

# Charts
if not df.empty:
    st.subheader("📌 Unique Miner Contribution")
    pow_df = df[df["Algorithm"].isin(["ProgPoW", "RandomX", "SHA256D"])]
    counts = pow_df["Address"].value_counts().reset_index()
    counts.columns = ["Address", "Blocks Mined"]
    fig = px.pie(counts, names="Address", values="Blocks Mined", title="Miner Share")
    st.plotly_chart(fig, use_container_width=True)

    if any(counts["Blocks Mined"] / counts["Blocks Mined"].sum() > 0.51):
        st.error("⚠️ WARNING: A miner has over 51% share!")

    st.subheader("📊 Blocks by Algorithm")
    grouped = pow_df.groupby(["Address", "Algorithm"]).size().reset_index(name="Blocks")
    fig2 = px.bar(grouped, x="Address", y="Blocks", color="Algorithm")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 Mined Blocks Timeline")
    pow_df.loc[:, 'Timestamp'] = pd.to_datetime(pow_df['Timestamp'])
    sorted_df = pow_df.sort_values("Timestamp")
    fig3 = px.line(sorted_df, x="Timestamp", y="Block Height", color="Algorithm", markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("📉 Difficulty Trends by Algorithm")
    diff_df = pow_df.copy()
    diff_df['Difficulty'] = pd.to_numeric(diff_df['Difficulty'], errors='coerce')
    for algo in ["ProgPoW", "RandomX", "SHA256D"]:
        sub_df = diff_df[diff_df["Algorithm"] == algo]
        if not sub_df.empty:
            fig_algo = px.line(
                sub_df,
                x="Timestamp",
                y="Difficulty",
                title=f"{algo} Difficulty Over Time"
            )
            st.plotly_chart(fig_algo, use_container_width=True)

    st.subheader("🧪 Expected vs Actual Distribution")
    expected = pd.DataFrame({"Algorithm": ["ProgPoW", "RandomX", "SHA256D", "Stake"], "Expected %": [35, 10, 5, 50]})
    actual = df["Algorithm"].value_counts(normalize=True).reset_index()
    actual.columns = ["Algorithm", "Actual %"]
    actual["Actual %"] *= 100
    merged = expected.merge(actual, on="Algorithm", how="left").fillna(0)
    fig4 = px.bar(merged.melt(id_vars="Algorithm"), x="Algorithm", y="value", color="variable", barmode="group")
    st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(df.sort_values("Block Height", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("No mining data available yet.")
