# Save this as miner_tracker.py

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import requests
import time
import argparse
import logging
from functools import lru_cache

class MinerAnalyzer:
    def __init__(self, interval=300, verbose=False):
        self.api_base_url = "https://explorer-api.veil-project.com/api/"
        self.session = requests.Session()
        self.address_totals = {}
        self.interval = interval
        self.miner_updates = []
        self.start_block = None
        self.last_processed_block = 0
        self.total_blocks_processed = 0
        self.start_time = time.time()
        self.colors = {'progpow': 'red', 'randomx': 'blue', 'sha256d': 'green'}
        self.verbose = verbose

        # Plot
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(9, 10))

        # Logging
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s'
        )

    def fetch_data_from_api(self, endpoint, data=None, method='POST'):
        url = self.api_base_url + endpoint
        try:
            if method == 'POST':
                response = self.session.post(url, json=data, timeout=10)
            else:
                response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.warning(f"Failed to fetch {endpoint}: {e}")
            return None

    def fetch_current_synced_block(self):
        data = self.fetch_data_from_api("BlockchainInfo", method='GET')
        if data:
            return data.get("currentSyncedBlock"), data.get("chainInfo", {}).get("bestblockhash")
        return None, None

    @lru_cache(maxsize=10000)
    def fetch_block(self, height=0, hash_hex=""):
        data = {"hash": hash_hex, "height": height, "offset": 0, "count": 1}
        return self.fetch_data_from_api("Block", data)

    def fetch_miner_address(self, block_info):
        if not block_info:
            return None, None
        transactions = block_info.get('transactions', [])
        block_data = block_info.get('block', {})
        proof_type = block_data.get('proof_type', "")
        algo_map = {4: "sha256d", 3: "randomx", 2: "progpow"}
        winning_algo = algo_map.get(proof_type, "stake")
        for transaction in transactions:
            outputs = transaction.get('outputs', [])
            if outputs:
                addresses = outputs[0].get('addresses', [])
                if addresses:
                    addr = addresses[0][:8]
                    return "Fastpool" if addr == "VHU81LE2" else addr, winning_algo
        return None, winning_algo

    def add_to_address_total(self, address, algo):
        if address not in self.address_totals:
            self.address_totals[address] = {'count': 0, 'winning_algo': algo}
        self.address_totals[address]['count'] += 1
        self.address_totals[address]['winning_algo'] = algo
        self.miner_updates.append((address, algo))

    def flush_miner_updates(self):
        try:
            df = pd.read_csv('miner_data.csv')
        except FileNotFoundError:
            df = pd.DataFrame(columns=['Miner Address', 'Block Count', 'Winning Algo'])

        for address, algo in self.miner_updates:
            if address in df['Miner Address'].values:
                df.loc[df['Miner Address'] == address, 'Block Count'] += 1
                df.loc[df['Miner Address'] == address, 'Winning Algo'] = algo
            else:
                new_row = pd.DataFrame({'Miner Address': [address], 'Block Count': [1], 'Winning Algo': [algo]})
                df = pd.concat([df, new_row], ignore_index=True)

        df.to_csv('miner_data.csv', index=False)
        self.miner_updates.clear()

    def update_plot(self, current_block):
        df = pd.DataFrame([(k, v['count'], v['winning_algo']) for k, v in self.address_totals.items()],
                          columns=['Miner Address', 'Block Count', 'Winning Algo'])
        df = df[df['Block Count'] > 0].sort_values(by='Block Count', ascending=False)

        self.ax.clear()
        self.ax.pie(df['Block Count'], labels=df['Miner Address'], autopct='%1.1f%%', pctdistance=0.85,
                    colors=[self.colors.get(algo, 'gray') for algo in df['Winning Algo']],
                    textprops={'color': 'green'},
                    wedgeprops=dict(edgecolor='black', linewidth=1))
        self.ax.set_title(f'Mining Block Distribution\nCurrent Block: {current_block}')
        self.ax.axis('equal')
        self.ax.legend(handles=[mpatches.Patch(color=color, label=algo) for algo, color in self.colors.items()],
                       title='Algorithms')
        plt.draw()
        plt.pause(0.001)

    def print_miner_info(self):
        print("\nMiner Stats:")
        for address, data in sorted(self.address_totals.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"{address}: {data['count']} blocks [{data['winning_algo']}]")

    def print_summary_stats(self):
        elapsed = time.time() - self.start_time
        rate = self.total_blocks_processed / elapsed if elapsed > 0 else 0
        print(f"\nSummary:")
        print(f"Total blocks processed: {self.total_blocks_processed}")
        print(f"Elapsed time: {elapsed:.2f} seconds")
        print(f"Average rate: {rate:.2f} blocks/sec")

    def run(self):
        while True:
            current_block, current_hash = self.fetch_current_synced_block()
            if not current_block or not current_hash:
                time.sleep(15)
                continue

            if self.start_block is None:
                self.start_block = current_block

            for h in range(self.last_processed_block + 1, current_block + 1):
                block_info = self.fetch_block(height=h)
                miner_address, algo = self.fetch_miner_address(block_info)
                if miner_address:
                    self.add_to_address_total(miner_address, algo)
                    self.total_blocks_processed += 1
                    if self.verbose:
                        logging.debug(f"Block {h} - {miner_address} [{algo}]")

            self.last_processed_block = current_block
            self.flush_miner_updates()
            self.update_plot(current_block)
            self.print_miner_info()
            self.print_summary_stats()
            time.sleep(self.interval)

def parse_args():
    parser = argparse.ArgumentParser(description="Veil Miner Distribution Tracker")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    analyzer = MinerAnalyzer(interval=args.interval, verbose=args.verbose)
    analyzer.run()
