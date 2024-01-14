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
        "count": 1
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch latest block information from Block. Status code: {response.status_code}")
        return None

def fetch_miner_address(blockInfo):
    #print("Debug: fetch_miner_address")
    if blockInfo is None:
        print("Error: blockInfo is None.")
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
    print("Debug: addToAddressTotal")
    global address_totals
    if address in address_totals:
        address_totals[address] += total
    else:
        address_totals[address] = total

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
        
def main():
    global best_block_hash, current_synced_block
    start_block = fetch_current_synced_block()
    plt.figure(figsize=(8, 9))  # Set the figure size
    plt.ion()  # Turn on interactive mode

    prev_synced_block, prev_best_block_hash = None, None
    # Initialize df as an empty DataFrame
    df = pd.DataFrame()
    last_processed_block = current_synced_block
    

    while True:
        current_synced_block, best_block_hash = fetch_current_synced_block()
        '''if current_synced_block == last_processed_block:
            time.sleep(5)
        else:
            print("Current block: ", current_synced_block)'''
        # Check if the block or block hash is still the same
        if current_synced_block == prev_synced_block and best_block_hash == prev_best_block_hash:
            #print("No new blocks found. Sleeping for 15 seconds...")
            time.sleep(5)
        else:
            print("Current block: ", current_synced_block)
                
            # Update the previous block and block hash
            prev_synced_block, prev_best_block_hash = current_synced_block, best_block_hash
            if current_synced_block and best_block_hash:
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

                # Flatten the dictionary
                    flattened_data = [(k, v['count'], v['winning_algo']) for k, v in address_totals.items()]

                    # Create the DataFrame
                    df = pd.DataFrame(flattened_data, columns=['Miner Address', 'Block Count', 'Winning Algo'])
                    df['Block Count'] = pd.to_numeric(df['Block Count'], errors='coerce')

                if 'Block Count' in df.columns and not df['Block Count'].dropna().empty:
                    df = df.sort_values(by='Block Count', ascending=False)
                    df.to_csv('miner_data.csv', index=False)  # Save the data to a CSV file

                    if not df.empty and not df['Miner Address'].isna().all():
                        plt.clf()  # Clear the current figure
                        colors = {'progpow': 'red', 'randomx': 'blue', 'sha256d': 'green'}
                        patches, texts, autotexts = plt.pie(df['Block Count'], labels=df['Miner Address'], autopct='%1.1f%%', pctdistance=0.85, colors=[colors.get(algo, 'gray') for algo in df['Winning Algo']], textprops={'color': 'green'}, wedgeprops=dict(edgecolor='black', linewidth=1))
                        plt.title(f'Mining Block Distribution in the Last {current_synced_block - start_block[0]} blocks\nCurrent Block Number: {current_synced_block}')
                        plt.xlabel('Block Distribution')
                        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                        plt.setp(autotexts, size=8, weight="bold", color='black')

                        # Define the colors for each algorithm
                        legend_patches = [mpatches.Patch(color=color, label=algo) for algo, color in colors.items()]

                        # Add the new legend to the plot
                        plt.legend(handles=legend_patches, title='Algorithms')

                        plt.draw()  # Draw the plot
                        plt.pause(0.001)  # Pause to allow the plot to update
                        plt.show()  # Display the figure

                        for miner_address in address_totals:
                            print("Miner Address: ", miner_address, "Block Count: ", address_totals[miner_address]['count'])
        
        #last_processed_block = current_synced_block
        time.sleep(15)  # Sleep for 15 seconds                

if __name__ == "__main__":
    main()