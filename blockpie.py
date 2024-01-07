import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

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
        return

    transactions = blockInfo.get('transactions')
    if transactions is None:
        print("Stake")
        return

    for transaction in transactions:
        outputs = transaction.get('outputs', [])
        if outputs:  # Check if outputs is not empty
            addresses = outputs[0].get('addresses', [])
            if addresses:  # Check if addresses is not empty
                miner_address = addresses[0][:8]  # Truncate to 8 characters
            else:
                miner_address = None
        else:
            miner_address = None

        if miner_address in address_totals:
            address_totals[miner_address] += 1
        elif miner_address is not None:
            address_totals[miner_address] = 1
        else:
            if "Stake" in address_totals:
                return

        return miner_address           

def addToAddressTotal(address, total):
    #print("Debug: addToAddressTotal")
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

def update_miner_csv(miner_address):
    #print("Debug: update_miner_csv")
    df = pd.read_csv('miner_data.csv')
    print(df.columns)  # This will print the column names
    if miner_address in df['Miner Address'].values:
        df.loc[df['Miner Address'] == miner_address, 'Block Count'] += 1
    else:
        new_row = pd.DataFrame({'Miner Address': [miner_address], 'Block Count': [1]})
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv('miner_data.csv', index=False)

def main():
    global best_block_hash, current_synced_block
    #counter = 0  # Initialize the counter
    #block_counter = 0  # Initialize the block counter
    start_block = fetch_current_synced_block()
    starting_24hr_block = start_block[0]
    ending_24hr_block = starting_24hr_block + 1440
    plt.figure(figsize=(10, 10))  # Set the figure size

    print("Starting Block: ", start_block)
    print("Starting 24hr Block: ", starting_24hr_block) 
    print("Ending 24hr Block: ", ending_24hr_block)
    plt.ion()  # Turn on interactive mode
    
    last_best_block_hash = best_block_hash  # Update the last best block hash
    last_synced_block = current_synced_block  # Update the last synced block

    while True:
        #print("Debug: main loop")
        current_synced_block, best_block_hash = fetch_current_synced_block()

        #if current_synced_block == ending_24hr_block:
         #   start_block = fetch_current_synced_block()
          #  starting_24hr_block = start_block[0]
           # ending_24hr_block = starting_24hr_block + 1440
        #else:
         #   continue #This willeventually be used to reset the 24hr block counter
                #take a screenshot of the plot every 24 hours, store it, then reset the plot and counter and start over.

        if current_synced_block and best_block_hash:
            if last_synced_block is not None and current_synced_block > last_synced_block + 1:
                # If there are missed blocks, fetch their information
                for block in range(last_synced_block + 1, current_synced_block):
                    #print("Debug: updating blocks")
                    block_info = fetch_latest_block_info(height=block)
                    miner_address = fetch_miner_address(blockInfo=block_info)
                    #print("Debug: miner_address: ", miner_address)

                    # Update the address_totals dictionary
                    #print("Debug: address_totals: ", address_totals)
                    if miner_address == "Stake":
                        continue
                    elif miner_address in address_totals:
                        address_totals[miner_address] += 1
                        #print("Debug: address_totals[miner_address]: ", address_totals[miner_address])
                    elif miner_address is not None:
                        address_totals[miner_address] = 1
                        #print("Debug: address_totals[miner_address]: ", address_totals[miner_address])
                    else:
                        continue

                    # Update the database with the new address and count
                    update_miner_csv(miner_address)

            if best_block_hash == last_best_block_hash:  # If the best block hash hasn't changed, skip this iteration
                time.sleep(15)
                continue

            miner_address = fetch_miner_address(blockInfo=fetch_latest_block_info(height=current_synced_block, hash_hex=best_block_hash))

            df = pd.DataFrame(list(address_totals.items()), columns=['Miner Address', 'Block Count'])
            df['Block Count'] = pd.to_numeric(df['Block Count'], errors='coerce')

            if not df['Block Count'].dropna().empty:
                #print("Debug: df['Block Count'].dropna().empty")
                df = df.sort_values(by='Block Count', ascending=False)
                df.to_csv('miner_data.csv', index=False)  # Save the data to a CSV file

                #counter += 1  # Increment the counter
                
                if not df.empty and not df['Miner Address'].isna().all():
                    #print("Debug: df['Miner Address'].isna().all()") 
                    
                    plt.clf()  # Clear the current figure

                    # Generate a list of colors for the pie slices
                    colors = plt.cm.viridis(np.linspace(0, 1, len(df)))

                    patches, texts, autotexts = plt.pie(df['Block Count'], labels=df['Miner Address'], autopct='%1.1f%%', pctdistance=0.85, colors=colors, textprops={'color': 'green'})

                    plt.title(f'Mining Block Distribution in the Last {current_synced_block - starting_24hr_block} blocks\nCurrent Block Number: {current_synced_block}')
                    plt.xlabel('Block Distribution')

                    # Equal aspect ratio ensures that pie is drawn as a circle.
                    plt.axis('equal')  

                    # Increase label size
                    plt.setp(autotexts, size=8, weight="bold", color='orange')

                    plt.draw()  # Draw the plot
                    plt.pause(0.001)  # Pause to allow the plot to update
                    #plt.show()  # Display the figure

                    # Print the miner address and block count
                    if not df.empty:
                        print("*******************************************")
                        print("Current list of miners: ")
                        for index, row in df.iterrows():                         
                            print("-------------------------------------------")
                            print(f"Miner Address: {row['Miner Address']}, Block Count: {row['Block Count']}")
                            print("-------------------------------------------")
                    print("*******************************************")        

                last_best_block_hash = best_block_hash  # Update the last best block hash
                last_synced_block = current_synced_block  # Update the last synced block

        else:
            print("Error: Unable to fetch current synced block information.")
        #print("Full loops: ", counter)
        time.sleep(15)
        #print("Debug: end of main loop")

if __name__ == "__main__":
    main()
    