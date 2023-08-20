import os
import random
import time
from datetime import datetime
import pandas as pd
import requests
from web3 import Web3, HTTPProvider
import json
import colorlog
import logging
from colorama import init, Fore

with open('config.json', 'r') as f:
    data = json.load(f)

# Extract configuration and contracts
config = data['config']
CONTRACTS_AND_QUANTITIES = data['contracts']

MIN_TRANSACTION_DELAY = config['MIN_TRANSACTION_DELAY']
MAX_TRANSACTION_DELAY = config['MAX_TRANSACTION_DELAY']
MIN_ACCOUNT_DELAY = config['MIN_ACCOUNT_DELAY']
MAX_ACCOUNT_DELAY = config['MAX_ACCOUNT_DELAY']
MIN_TARGET_TXNS = config['MIN_TARGET_TXNS']
MAX_TARGET_TXNS = config['MAX_TARGET_TXNS']
SHUFFLE_ACCOUNTS = config['SHUFFLE_ACCOUNTS']
EXCEL_PATH = config['EXCEL_PATH']

# Helper Functions
def SetupGayLogger(logger_name):
    """
    SetupGayLogger initializes a colorful logging mechanism, presenting each log message in a beautiful
    rainbow sequence. The function accepts a logger name and returns a logger instance that can be used
    for logging messages.

    Parameters:
    - logger_name (str): A name for the logger.

    Returns:
    - logger (Logger): A configured logger instance.
    """

    # Initialize the colorama library, which provides an interface for producing colored terminal text.
    init()

    def rainbow_colorize(text):
        """
        Transforms a given text into a sequence of rainbow colors.

        Parameters:
        - text (str): The text to be colorized.

        Returns:
        - str: The rainbow colorized text.
        """
        # Define the sequence of colors to be used.
        colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
        colored_message = ''

        # For each character in the text, assign a color from the sequence.
        for index, char in enumerate(text):
            color = colors[index % len(colors)]
            colored_message += color + char

        # Return the colorized text and reset the color.
        return colored_message

    class RainbowColoredFormatter(colorlog.ColoredFormatter):
        """
        Custom logging formatter class that extends the ColoredFormatter from the colorlog library.
        This formatter first applies rainbow colorization to the entire log message before using the
        standard level-based coloring.
        """

        def format(self, record):
            """
            Format the log record. Overridden from the base class to apply rainbow colorization.

            Parameters:
            - record (LogRecord): The log record.

            Returns:
            - str: The formatted log message.
            """
            # First rainbow colorize the entire message.
            message = super().format(record)
            rainbow_message = rainbow_colorize(message)
            return rainbow_message

    # Obtain an instance of a logger for the provided name.
    logger = colorlog.getLogger(logger_name)

    # Ensure that if there are any pre-existing handlers attached to this logger, they are removed.
    # This prevents duplicate messages from being displayed.
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    # Create a stream handler to output log messages to the console.
    handler = colorlog.StreamHandler()

    # Assign the custom formatter to the handler.
    handler.setFormatter(
        RainbowColoredFormatter(
            "|%(log_color)s%(asctime)s| - [%(name)s] - %(levelname)s - %(message)s",
            datefmt=None,
            reset=False,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
    )

    # Attach the handler to the logger.
    logger.addHandler(handler)

    # Set the minimum logging level to DEBUG. This means messages of level DEBUG and above will be processed.
    logger.setLevel(logging.DEBUG)

    return logger
def create_excel_file(file_path):
    """
    Create a new Excel file with columns for private keys, proxies, target transaction numbers, and timestamp.
    """
    df = pd.DataFrame(columns=['Private_Key', 'Proxy', 'Target_Txns', 'Time_Stamp', 'Acc_delay', 'total_mint'])

    # Load private keys from the file
    with open('pkey.txt', 'r') as f:
        private_keys = [line.strip() for line in f.readlines()]

    proxies_list = []
    # Load proxies from file if required

    with open('proxies.txt', 'r') as f:
        proxies_list = [line.strip() for line in f.readlines()]
        proxies_list.extend(proxies_list * (len(private_keys) // len(proxies_list)))

    # Populate Excel rows with private keys, proxies, random target transactions, and the 1969 timestamp
    for pkey, proxy in zip(private_keys, proxies_list):
        target_txns = random.randint(MIN_TARGET_TXNS, MAX_TARGET_TXNS)
        target_delay = random.randint(MIN_ACCOUNT_DELAY, MAX_ACCOUNT_DELAY)
        timestamp_1969 = "1969-01-01 00:00:00"
        df = df._append({'Private_Key': pkey, 'Proxy': proxy, 'Target_Txns': target_txns, 'Time_Stamp': timestamp_1969, 'Acc_delay': target_delay, 'total_mint': 0},
                       ignore_index=True)

    # Save the DataFrame to an Excel file
    df.to_excel(file_path, index=False)
def mint_tokens(logger, sender_address, contract_address, quantity, private_key, proxy=None):
    """
    Mint tokens using the provided contract address, quantity, and private key.
    Optionally, use a proxy for the transaction.
    """
    try:
        # Set up the session and optionally the proxy
        session = requests.Session()
        if proxy:
            credentials, ip_port = proxy.split('@')
            session.proxies = {
                "http": f"http://{credentials}@{ip_port}",
                "https": f"http://{credentials}@{ip_port}",
            }

        # Set the web3 provider with the current session
        w3.provider = HTTPProvider('https://rpc.zora.energy', session=session)
        contract_address = w3.to_checksum_address(contract_address)
        # Load the contract and prepare the transaction data
        contract = w3.eth.contract(address=contract_address, abi=abi)
        transaction_data = contract.functions.mint(quantity)._encode_transaction_data()

        # Create and send the transaction
        txn_params = {
            'to': contract_address,
            'from': sender_address,
            'data': transaction_data
        }

        # Round to 6 digits after the decimal
        rounded_value = round(random.uniform(0.005, 0.05), 6)

        estimated_gas = w3.eth.estimate_gas(txn_params)
        transaction = {
            'to': contract_address,
            'value': 0,
            'gas': estimated_gas,
            'maxPriorityFeePerGas': int(w3.to_wei(rounded_value, 'gwei')),
            'maxFeePerGas': int(w3.to_wei(rounded_value, 'gwei')),
            'nonce': w3.eth.get_transaction_count(sender_address),
            'data': transaction_data,
            'chainId': 7777777
        }
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

        if receipt['status'] == 1:
            logger.info(f"Transaction successfully completed:")
            logger.info(f"https://explorer.zora.energy/tx/{txn_hash.hex()}")
            with open("successful_tx.txt", "a") as f:
                f.write(f"Address {sender_address} | {txn_hash.hex()}\n")
            return 1
        elif receipt['status'] == 0:
            logger.warning(f"Transaction was unsuccessful: https://explorer.zora.energy/tx/{txn_hash.hex()}")
            with open("failed_tx.txt", "a") as f:
                f.write(f"Address {sender_address} | {txn_hash.hex()}\n")
            return 0

    except Exception as e:
        logger.error(f"Error processing wallet {sender_address}: {e}")
        return 0
def get_time_difference_in_hours(idx, df):
    time_difference = datetime.now() - datetime.strptime(df.at[idx, 'Time_Stamp'], "%Y-%m-%d %H:%M:%S")
    return round(time_difference.total_seconds() / 3600, 1)

# Main Logic
if not os.path.exists(EXCEL_PATH):
    create_excel_file(EXCEL_PATH)

df = pd.read_excel(EXCEL_PATH)

private_keys = df['Private_Key'].tolist()
proxies_list = df['Proxy'].tolist()

# Optionally shuffle the accounts for randomness
if SHUFFLE_ACCOUNTS:
    combined = list(zip(private_keys, proxies_list))
    random.shuffle(combined)
    private_keys, proxies_list = zip(*combined)

# Connect to the Ethereum RPC node
w3 = Web3(HTTPProvider('https://rpc.zora.energy'))

# Load the ABI for the contract
with open('abi.json', 'r') as f:
    abi = json.load(f)

# Infinite loop to continuously mint for eligible accounts.
while True:
    eligible_id_found = False
    sleep_delay = 100
    # Process each private key and associated proxy
    all_indices = list(range(len(private_keys)))
    random.shuffle(all_indices)

    print("Subscribe: https://t.me/CryptoBub_ble")

    for idx in all_indices:
        private_key = private_keys[idx]
        proxy = proxies_list[idx]
        # Randomly select a contract and its quantity
        contract_data = random.choice(CONTRACTS_AND_QUANTITIES)

        repeat_mint = df.at[idx, 'Target_Txns']
        account_delay = df.at[idx, 'Acc_delay']
        total_mint = df.at[idx, 'total_mint']
        nugger = SetupGayLogger(f'Wallet {idx}')

        diferents = get_time_difference_in_hours(idx, df)
        sender_address = w3.eth.account.from_key(private_key).address

        if total_mint >= repeat_mint:
            nugger.info(f"Max transactions reached for wallet {sender_address}. Skipping...")
            continue
        if diferents < account_delay:
            nugger.info(f"Wallet {sender_address} time different {diferents}h - less that target delay {account_delay}h. Skipping...")
            continue

        eligible_id_found = True
        sleep_delay = 100

        status = mint_tokens(nugger, sender_address, contract_data["address"], contract_data["quantity"], private_key, proxy)

        if status:
            df.at[idx, 'total_mint'] += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df.at[idx, 'Time_Stamp'] = timestamp
            df.to_excel(EXCEL_PATH, index=False)
            nugger.warning(f"Updated timestamp for wallet {sender_address} to {timestamp}")
        else:
            continue
        # Wait for a random time before the next transaction
        delay = random.randint(MIN_TRANSACTION_DELAY, MAX_TRANSACTION_DELAY)
        nugger.info(f"Waiting {delay} second before next mint...")
        time.sleep(delay)

    if not eligible_id_found:
        # If no eligible IDs were found in this iteration, increase the sleep delay
        nugger_junior = SetupGayLogger("Mister_chocolate")
        sleep_delay *= 3.14
        nugger_junior.warning(f"No wallet available for mint, Chill {sleep_delay} seconds before next check...")
        nugger_junior.warning("While waiting you should definitely subscribe to my chanel | https://t.me/CryptoBub_ble")
        time.sleep(sleep_delay)
