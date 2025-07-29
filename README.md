# 🧱 BlockPie — Veil Miner Dashboard

📍 GitHub Repo: [https://github.com/ohcee/Veil-blockpie](https://github.com/ohcee/Veil-blockpie)

**BlockPie** is a real-time dashboard that monitors which miners are winning Proof-of-Work blocks on the [Veil Project](https://veil-project.com) blockchain.

It fetches block data every 5 minutes and displays pie charts, bar graphs, difficulty trends, and miner distribution insights. The dashboard highlights potential 51% threats, compares expected vs actual mining distribution, and stores history locally for deeper analysis.

---

## ⚙️ Features

- ⛏️ Pie chart showing who mined the most PoW blocks
- 📊 Bar graph of address share by algorithm (ProgPoW, RandomX, SHA256D)
- 📈 Line graph of difficulty over time for each PoW algorithm
- 🧪 Expected vs Actual block distribution
- ⚠️ 51% dominance detection
- 🔁 Auto-refreshes every 5 minutes (or manually via browser reload)
- 💾 Stores block data in `miner_data.csv` for historical analysis

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ohcee/Veil-blockpie.git
cd Veil-blockpie
```
2. Install Dependencies
```bash
pip install -r requirements.txt
```
- Or install manually:
```bash
pip install streamlit requests pandas plotly streamlit-autorefresh numpy
```
3. Run the Dashboard
```bash
streamlit run blockpie.py
```
   - Make sure you're using Python 3.8+.

   - RandomX hashrate is estimated based on block frequency and adjusted for its 10% share

   - Works best when left running over time to analyze block trends

   - Miner warning is triggered if any single address exceeds 51% of blocks in the tracked window

   - Pulls block data from explorer.veil-project.com every 5 minutes

   - Saves block height, timestamp, mining address, algorithm, and difficulty to miner_data.csv

   - Displays the latest mining activity and trends with Streamlit + Plotly

   - Detects PoW miner dominance and deviation from expected block proportions
