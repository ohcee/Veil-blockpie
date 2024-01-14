import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches


# Initialize global variables
address_totals = {}
#countdown = 1440
best_block_hash = None
current_synced_block = None

def fetch_latest_block_info(height=0, hash_hex=""):
    url = "https://explorer-api.veil-project.com/api/Block"
    data = {
        "hash": hash_hex,
        "height": height,
        "offset": 0,
        "count": 1,
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch latest block information from Block. Status code: {response.status_code}")
        return None
    
def fetch_block_before(height=0, hash_hex=""):
    url = "https://explorer-api.veil-project.com/api/Block"
    data = {
        "hash": hash_hex,
        "height": height,
        "offset": 0,
        "count": 1
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        response_data = response.json()
        #print("response_data: ", response_data)
        prev_block = response_data.get('prevBlock', {})
        #print("prev_block: ", prev_block)
        if prev_block:
            prev_block_info = prev_block.get('hash', 'height')
            if prev_block_info:
                prev_block_height = prev_block.get('height')
                #print("prev_block_height: ", prev_block_height)
                prev_block_hash = prev_block.get('hash')
                #print("prev_block_hash: ", prev_block_hash)
                fetch_latest_block_info(height=prev_block_height, hash_hex=prev_block_hash)
                miner_address, winning_algo = fetch_miner_address(fetch_latest_block_info(height=prev_block_height, hash_hex=prev_block_hash))
                if miner_address and winning_algo:
                    addToAddressTotal(miner_address, 1)
            else:
                print("Error: hash or height does not exist in prevBlock")
                return None, None
        else:
            print("Error: prevBlock does not exist in response_data")
            return None, None        
        return response.json()
    else:
        print(f"Error: Unable to fetch latest block information from Block. Status code: {response.status_code}")
        return None, None  

def fetch_miner_address(blockInfo):
    #print("Debug: fetch_miner_address")
    if blockInfo is None or isinstance(blockInfo, tuple):
        print("Error: blockInfo is None or not a dictionary.")
        return None, None

    transactions = blockInfo.get('transactions')
    if transactions is None:
        #print("Stake")
        return None, None
    
    block_data = blockInfo.get('block', [])
    #print("block_data: ", block_data)
    proof_type = block_data.get('proof_type')
    #print("proof_type: ", proof_type)
    winning_algo = ""
    
    if proof_type == 4:
        print("sha256d block found")
        winning_algo = "sha256d"
    elif proof_type == 3:
        print("randomx block found")
        winning_algo = "randomx"
    elif proof_type == 2:
        print("progpow block found")
        winning_algo = "progpow"
    else:
        print("stake block found(Not counted)")
        winning_algo = "stake"
    #print("winning_algo: ", winning_algo, "for block: ", current_synced_block)
    
    miner_address = None
    for transaction in transactions:
        outputs = transaction.get('outputs', [])
        if outputs:  # Check if outputs is not empty
            addresses = outputs[0].get('addresses', [])
            if addresses:  # Check if addresses is not empty
                miner_address = addresses[0][:8]  
                if miner_address == "VHU81LE2":
                    miner_address = "Fastpool"
            else:
                miner_address = None
        else:
            miner_address = None

        if miner_address == "Stake":
            continue
        else:
            break
    #print("miner_address: ", miner_address, "winning_algo: ", winning_algo) 
    return miner_address, winning_algo

def addToAddressTotal(address, total):
    #print("Debug: addToAddressTotal")
    global address_totals
    if address in address_totals and isinstance(address_totals[address], dict):
        address_totals[address]['count'] += total
    elif address in address_totals:
        # If the value is not a dictionary, create a new dictionary and update the count
        address_totals[address] = {'count': total, 'winning_algo': None}
    else:
        # If the address is not in address_totals, add it with the count and winning_algo
        address_totals[address] = {'count': total, 'winning_algo': None}

def fetch_current_synced_block():
    #print("Debug: fetch_current_synced_block")
    url = "https://explorer-api.veil-project.com/api/BlockchainInfo"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        current_synced_block = data.get("currentSyncedBlock")
        best_block_hash = data.get("chainInfo", {}).get("bestblockhash")
        return current_synced_block, best_block_hash
    else:
        print(f"Error: Unable to fetch current synced blockchaininfo information. Status code: {response.status_code}")
        return None, None

def update_miner_csv(miner_address, winning_algo):
    df = pd.read_csv('miner_data.csv')
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
    if start_block is None:
        return current_synced_block
    return start_block

def update_prev_block_info(current_synced_block, best_block_hash):
    miner_address, winning_algo = fetch_miner_address(fetch_latest_block_info(height=current_synced_block, hash_hex=best_block_hash))
    if miner_address == "VHU81LE2":
        miner_address = "Fastpool"
    if miner_address:
        if miner_address in address_totals:
            address_totals[miner_address]['count'] += 1
            address_totals[miner_address]['winning_algo'] = winning_algo
        else:
            address_totals[miner_address] = {'count': 1, 'winning_algo': winning_algo}
        update_miner_csv(miner_address, winning_algo)

def process_missed_blocks(start_block, last_processed_block, current_synced_block):
    if start_block is not None and current_synced_block - last_processed_block > 1 and last_processed_block >= start_block:
        print("Debug: missed blocks")
        missed_block_start = max(last_processed_block + 1, start_block)
        print("missed_block_start: ", missed_block_start)
        if missed_block_start < current_synced_block:
            # Include the current block in the range
            for prev_block_height in range(missed_block_start, current_synced_block + 1):
                if prev_block_height != current_synced_block:
                    prev_block_info = fetch_block_before(height=prev_block_height)
                    if prev_block_info:
                        miner_address, winning_algo = fetch_miner_address(prev_block_info)
                        if miner_address:
                            if miner_address in address_totals and isinstance(address_totals[miner_address], dict):
                                address_totals[miner_address]['count'] += 1
                                address_totals[miner_address]['winning_algo'] = winning_algo
                            else:
                                address_totals[miner_address] = {'count': 1, 'winning_algo': winning_algo}
                            update_miner_csv(miner_address, winning_algo)
                            print(f"Block info added for block: {prev_block_height}, Miner: {miner_address}, Winning Algo: {winning_algo}")

def create_and_show_plot(start_block, current_synced_block):
    flattened_data = [(k, v['count'], v['winning_algo']) for k, v in address_totals.items()]
    df = pd.DataFrame(flattened_data, columns=['Miner Address', 'Block Count', 'Winning Algo'])
    df['Block Count'] = pd.to_numeric(df['Block Count'], errors='coerce')

    if 'Block Count' in df.columns and not df['Block Count'].dropna().empty:
        df = df.sort_values(by='Block Count', ascending=False)
        df.to_csv('miner_data.csv', index=False)
        
        plt.clf()
        colors = {'progpow': 'red', 'randomx': 'blue', 'sha256d': 'green'}
        patches, texts, autotexts = plt.pie(df['Block Count'], labels=df['Miner Address'], autopct='%1.1f%%', pctdistance=0.85, colors=[colors.get(algo, 'gray') for algo in df['Winning Algo']], textprops={'color': 'green'}, wedgeprops=dict(edgecolor='black', linewidth=1))
        plt.title(f'Mining Block Distribution in the Last {current_synced_block - start_block} blocks\nCurrent Block Number: {current_synced_block}')
        plt.xlabel('Block Distribution')
        plt.axis('equal')
        plt.setp(autotexts, size=8, weight="bold", color='black')
        legend_patches = [mpatches.Patch(color=color, label=algo) for algo, color in colors.items()]
        plt.legend(handles=legend_patches, title='Algorithms')
        plt.draw()
        plt.pause(0.001)
        plt.show()

def main():
    global best_block_hash, current_synced_block
    initialize_plot()

    prev_synced_block, prev_best_block_hash = None, None
    df = pd.DataFrame()
    last_processed_block = 0

    start_block = None

    while True:
        current_synced_block, best_block_hash = fetch_and_update_current_synced_block()

        if current_synced_block == prev_synced_block and best_block_hash == prev_best_block_hash:
            print("No new blocks. Waiting for 30 seconds...")
            time.sleep(30)
        else:
            print("Current block: ", current_synced_block)
            print("Start block: ", start_block)

            start_block = update_start_block(start_block, current_synced_block)

            prev_synced_block, prev_best_block_hash = current_synced_block, best_block_hash

            update_prev_block_info(current_synced_block, best_block_hash)

            process_missed_blocks(start_block, last_processed_block, current_synced_block)

            last_processed_block = current_synced_block

            create_and_show_plot(start_block, current_synced_block)

        print("\nMiner Information: ")
        print("*******************************************")
        # Sort address_totals by block count in descending order
        sorted_miner_info = sorted(address_totals.items(), key=lambda x: x[1]['count'], reverse=True)
        for miner_address, data in sorted_miner_info:
            print("Miner Address: ", miner_address, "Block Count: ", data['count'])
            print("-------------------------------------------")
        print("*******************************************\n")

        time.sleep(30)

if __name__ == "__main__":
    main()
