import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Initialize global variables
address_totals = {}
best_block_hash = None
current_synced_block = None
api_base_url = "https://explorer-api.veil-project.com/api/"

def fetch_data_from_api(endpoint, data):
    url = api_base_url + endpoint
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch data from {endpoint}. Status code: {response.status_code}")
        return None

def fetch_latest_block_info(height=0, hash_hex=""):
    data = {
        "hash": hash_hex,
        "height": height,
        "offset": 0,
        "count": 1,
    }
    return fetch_data_from_api("Block", data)

def fetch_block_before(height=0, hash_hex=""):
    fetched_blocks = {}
    if height in fetched_blocks:
        return fetched_blocks[height]
    block_info = fetch_latest_block_info(height, hash_hex)
    if block_info:
        prev_block = block_info.get('prevBlock', {})
        if prev_block:
            prev_block_height = prev_block.get('height')
            prev_block_hash = prev_block.get('hash')
            block_info = fetch_latest_block_info(height=prev_block_height, hash_hex=prev_block_hash)
            miner_address, winning_algo = fetch_miner_address(block_info)
            if miner_address and winning_algo:
                add_to_address_total(miner_address, 1)
            fetched_blocks[height] = block_info
        else:
            print("Error: prevBlock does not exist in response data")
    return block_info

def fetch_miner_address(block_info):
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
                miner_address = addresses[0][:8]
                if miner_address == "VHU81LE2":
                    miner_address = "Fastpool"
                return miner_address, winning_algo
    return None, winning_algo

def add_to_address_total(address, total):
    if address in address_totals:
        address_totals[address]['count'] += total
    else:
        address_totals[address] = {'count': total, 'winning_algo': None}

def fetch_current_synced_block():
    response = requests.get(api_base_url + "BlockchainInfo")
    if response.status_code == 200:
        data = response.json()
        current_synced_block = data.get("currentSyncedBlock")
        best_block_hash = data.get("chainInfo", {}).get("bestblockhash")
        return current_synced_block, best_block_hash
    else:
        print(f"Error: Unable to fetch current synced blockchain info. Status code: {response.status_code}")
        return None, None

def update_miner_csv(miner_address, winning_algo):
    try:
        df = pd.read_csv('miner_data.csv')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['Miner Address', 'Block Count', 'Winning Algo'])

    if miner_address in df['Miner Address'].values:
        df.loc[df['Miner Address'] == miner_address, 'Block Count'] += 1
        df.loc[df['Miner Address'] == miner_address, 'Winning Algo'] = winning_algo
    else:
        new_row = pd.DataFrame({'Miner Address': [miner_address], 'Block Count': [1], 'Winning Algo': [winning_algo]})
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv('miner_data.csv', index=False)

def initialize_plot():
    plt.figure(figsize=(8, 9))
    plt.ion()

def fetch_and_update_current_synced_block():
    while True:
        current_synced_block, best_block_hash = fetch_current_synced_block()
        if current_synced_block is not None and best_block_hash is not None:
            return current_synced_block, best_block_hash
        print("Error: Unable to fetch current synced block information. Retrying...")
        time.sleep(15)

def update_start_block(start_block, current_synced_block):
    return start_block or current_synced_block

def update_prev_block_info(current_synced_block, best_block_hash):
    block_info = fetch_latest_block_info(height=current_synced_block, hash_hex=best_block_hash)
    miner_address, winning_algo = fetch_miner_address(block_info)
    if miner_address:
        add_to_address_total(miner_address, 1)
        address_totals[miner_address]['winning_algo'] = winning_algo
        update_miner_csv(miner_address, winning_algo)

def process_missed_blocks(start_block, last_processed_block, current_synced_block):
    if start_block and current_synced_block - last_processed_block > 1 and last_processed_block >= start_block:
        print("Finding missed blocks")
        for prev_block_height in range(last_processed_block + 1, current_synced_block + 1):
            if prev_block_height != current_synced_block:
                prev_block_info = fetch_block_before(height=prev_block_height)
                if prev_block_info:
                    miner_address, winning_algo = fetch_miner_address(prev_block_info)
                    if miner_address:
                        add_to_address_total(miner_address, 1)
                        address_totals[miner_address]['winning_algo'] = winning_algo
                        update_miner_csv(miner_address, winning_algo)

def create_and_show_plot(start_block, current_synced_block):
    df = pd.DataFrame([(k, v['count'], v['winning_algo']) for k, v in address_totals.items()],
                      columns=['Miner Address', 'Block Count', 'Winning Algo'])
    df['Block Count'] = pd.to_numeric(df['Block Count'], errors='coerce')

    if 'Block Count' in df.columns and not df['Block Count'].dropna().empty:
        df = df.sort_values(by='Block Count', ascending=False)
        df.to_csv('miner_data.csv', index=False)
        plt.clf()
        colors = {'progpow': 'red', 'randomx': 'blue', 'sha256d': 'green'}
        plt.pie(df['Block Count'], labels=df['Miner Address'], autopct='%1.1f%%', pctdistance=0.85,
                colors=[colors.get(algo, 'gray') for algo in df['Winning Algo']], textprops={'color': 'green'},
                wedgeprops=dict(edgecolor='black', linewidth=1))
        plt.title(f'Mining Block Distribution in the Last {current_synced_block - start_block} blocks\nCurrent Block Number: {current_synced_block}')
        plt.xlabel('Block Distribution')
        plt.axis('equal')
        plt.legend(handles=[mpatches.Patch(color=color, label=algo) for algo, color in colors.items()], title='Algorithms')
        plt.draw()
        plt.pause(0.001)
        plt.show()

def print_miner_info():
    print("\nMiner Information: ")
    print("**********************************************")
    for miner_address, data in sorted(address_totals.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"* Miner Address: {miner_address} Block Count: {data['count']} *")
        print("* ---------------------------------------- *")
    print("**********************************************\n")        

def main():
    global best_block_hash, current_synced_block
    initialize_plot()

    prev_synced_block, prev_best_block_hash = None, None
    last_processed_block = 0
    start_block = None

    while True:
        current_synced_block, best_block_hash = fetch_and_update_current_synced_block()
        print("############################")
        print(f"#  Start block: {start_block} #")
        print(f"#  Current block: {current_synced_block} #")
        print("############################")

        start_block = update_start_block(start_block, current_synced_block)
        update_prev_block_info(current_synced_block, best_block_hash)
        process_missed_blocks(start_block, last_processed_block, current_synced_block)
        last_processed_block = current_synced_block

        create_and_show_plot(start_block, current_synced_block)
        print_miner_info()

        time.sleep(300) 

if __name__ == "__main__":
    main()


