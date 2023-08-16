import requests
from web3 import Web3, HTTPProvider
import json
import time
import random
import csv

# Configuration
MIN_TRANSACTION_DELAY = 30                 # Minimum random delay between transactions
MAX_TRANSACTION_DELAY = 100                # Maximum random delay between transactions
MIN_ACCOUNT_DELAY = 600                    # Minimum delay between different wallets
MAX_ACCOUNT_DELAY = 900                    # Maximum delay between different wallets
MIN_REPEAT_MINTS = 3                       # Minimum number of mint repetitions for an account
MAX_REPEAT_MINTS = 9                       # Maximum number of mint repetitions for an account
USE_PROXIES = True                         # Use proxies or not (For CIS countries, proxies are mandatory, otherwise RPC block. You can use 1 for all accounts)
SHUFFLE_ACCOUNTS = True                    # Shuffle accounts or not

# Each account will take a random NFT from this contract. Do not modify.
CONTRACTS_AND_QUANTITIES = [
    {"address": "0x4de73D198598C3B4942E95657a12cBc399E4aDB5", "quantity": 1},
    {"address": "0x53cb0B849491590CaB2cc44AF8c20e68e21fc36D", "quantity": 3},
    {"address": "0xca5F4088c11B51c5D2B9FE5e5Bc11F1aff2C4dA7", "quantity": 2},
    {"address": "0x266b7E8Df0368Dd4006bE5469DD4EE13EA53d3a4", "quantity": 3},
    {"address": "0xCc4FF6BB314055846e46490B966745E869546B4a", "quantity": 100},
    {"address": "0x9eAE90902a68584E93a83D7638D3a95ac67FC446", "quantity": 3},
    {"address": "0x4073a52A3fc328D489534Ab908347eC1FcB18f7f", "quantity": 3},
    {"address": "0x12B93dA6865B035AE7151067C8d264Af2ae4be8E", "quantity": 10},
    {"address": "0x266b7E8Df0368Dd4006bE5469DD4EE13EA53d3a4", "quantity": 3},
    {"address": "0xC47ADb3e5dC59FC3B41d92205ABa356830b44a93", "quantity": 2},
    {"address": "0xDcFB6cB9512E50dC54160cB98E5a00B3383F6A53", "quantity": 100}
]  # kept as it is

# Load the contract ABI
with open('abi.json', 'r') as f:
    abi = json.load(f)

# Load the private keys
with open('pkey.txt', 'r') as f:
    private_keys = [line.strip() for line in f]

# Shuffle accounts if necessary
if SHUFFLE_ACCOUNTS:
    random.shuffle(private_keys)

# Load proxies list
if USE_PROXIES:
    with open('proxies.txt', 'r') as f:
        proxies_list = [line.strip() for line in f]

# Ensure that the number of proxies matches the number of private keys
# If there are more private keys than proxies, then duplicates will be created for proxies
while len(proxies_list) < len(private_keys):
    proxies_list.extend(proxies_list)

# Associate each private key with a specific proxy
wallet_proxy_pairs = list(zip(private_keys, proxies_list))


w3 = Web3(HTTPProvider('https://rpc.zora.energy'))

if not w3.is_connected():
    print("Not connected to RPC")
    exit()

print("Connected to RPC")

# Create a CSV file to store the results
with open('transactions.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['Wallet', 'Contract Address', 'Transaction Link', 'Status'])

# Process each private key
for index, (private_key, proxy) in enumerate(wallet_proxy_pairs, 1):
    # Setting up the request session with the associated proxy
    session = requests.Session()
    proxy_data = proxy.split('@')
    credentials = proxy_data[0]
    ip_port = proxy_data[1]
    session.proxies = {
        "http": f"http://{credentials}@{ip_port}",
        "https": f"http://{credentials}@{ip_port}",
    }
    w3.provider = HTTPProvider('https://rpc.zora.energy', session=session)
    sender_address = w3.eth.account.from_key(private_key).address
    try:
        # Choose a random contract
        contract_and_quantity = random.choice(CONTRACTS_AND_QUANTITIES)
        contract_address = contract_and_quantity["address"]
        quantity_to_mint = contract_and_quantity["quantity"]

        # Initialize the contract
        contract = w3.eth.contract(address=contract_address, abi=abi)
        mint_function = contract.functions.mint(quantity_to_mint)
        transaction_data = mint_function._encode_transaction_data()

        # Choose a random number of repeat mints
        repeat_mints = random.randint(MIN_REPEAT_MINTS, MAX_REPEAT_MINTS)
        account_delay = random.randint(MIN_ACCOUNT_DELAY, MAX_ACCOUNT_DELAY)
        for repeat_index in range(repeat_mints):
            estimated_gas = w3.eth.estimate_gas({
                'to': contract_address,
                'from': sender_address,
                'data': transaction_data
            })

            # Create the transaction object
            transaction = {
                'to': contract_address,
                'value': 0,
                'gas': estimated_gas,
                'maxPriorityFeePerGas': int(w3.to_wei('0.0005', 'gwei')),
                'maxFeePerGas': int(w3.to_wei('0.0005', 'gwei')),
                'nonce': w3.eth.get_transaction_count(sender_address),
                'data': transaction_data,
                'chainId': 7777777
            }

            # Sign and send the transaction
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Wait for the transaction to complete
            receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

            # Check the transaction status and write to the CSV
            status = "Successful" if receipt.status == 1 else "Failed"
            with open('transactions.csv', 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(
                    [sender_address, contract_address, f"https://explorer.zora.energy/tx/{txn_hash.hex()}", status])

            # Display the transaction information
            checksum_address = w3.to_checksum_address(sender_address)
            print(f"Wallet: {checksum_address} [{index}/{len(private_keys)}]")
            print(f"Repeat counts for this wallet: [{repeat_index + 1}/{repeat_mints}]")
            if receipt.status == 1:
                print(f"Transaction successfully completed: https://explorer.zora.energy/tx/{txn_hash.hex()}")
            else:
                print(f"Transaction was rejected: https://explorer.zora.energy/tx/{txn_hash.hex()}")
            delay = random.randint(MIN_TRANSACTION_DELAY, MAX_TRANSACTION_DELAY)
            print(f"Delay between transactions: {delay} seconds\n" + '-' * 20)
            time.sleep(delay)
        print(f"Delay between wallets: {account_delay} seconds\n" + '-' * 20)
        time.sleep(account_delay)

    except Exception as e:
        print(f"Error processing wallet {sender_address}: {e}")
