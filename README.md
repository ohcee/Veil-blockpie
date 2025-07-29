# BlockPie 🥧

BlockPie is a real-time miner tracking and analytics dashboard for the [Veil Project](https://veil-project.com) Proof-of-Work blockchain. It monitors newly mined blocks using data from the public Veil Explorer API and displays live mining statistics, including block distribution per miner address, mining algorithm breakdown (ProgPoW, RandomX, SHA256D), and network difficulty.

It helps reveal who is mining blocks, how often, and how dominant any one miner is — right in a simple web-based interface.

---

## 🚀 Features

- ⛏️ Displays top miners and how many blocks each has found  
- 📊 Shows mining algorithm distribution (ProgPoW / RandomX / SHA256D)  
- 🔍 Detects missed blocks and updates miner block counts  
- ⏱️ Shows estimated network hashrates and difficulty per algorithm  
- 🧠 Warns about potential 51% miner dominance  
- 🕒 Automatically refreshes every 5 minutes, with optional manual refresh  
- 📈 Graphs include pie charts, bar charts, and difficulty history  
- 🎯 Filtered to only PoW blocks — staking blocks are ignored  

---

## 🛠 Requirements

Install the required Python libraries:

```bash
pip install streamlit requests pandas matplotlib
```
🧩 How to Use

    Clone or download this repository

    Ensure Python 3.8+ is installed on your system

    Open a terminal in the project folder and run:
```bash
streamlit run dashboard.py
```
    A local web app will open automatically in your browser

    Let it run in the background to track mining activity over time

📡 Notes

    Data is pulled from https://explorer-api.veil-project.com

    Only PoW blocks are used for miner tracking (staking blocks are ignored)

    RandomX hashrate is estimated based on block frequency and adjusted for its 10% share

    Works best when left running over time to analyze block trends

    Miner warning is triggered if any single address exceeds 51% of blocks in the tracked window
