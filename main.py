import requests
from web3 import Web3, HTTPProvider
import json
import time
import random
import logging
import pandas as pd
import os
from tqdm import tqdm

# ---------------------- CONFIGURATION ----------------------

CONFIG = {
    "DELAY_MIN": 30,                # Рандомная задержка между транзакциями ОТ
    "DELAY_MAX": 100,               # Рандомная задержка между транзакциями ДО
    "ACCOUNT_DELAY_MIN": 600,       # Задержка между разными кошельками ОТ
    "ACCOUNT_DELAY_MAX": 900,       # Задержка между разными кошельками ДО
    "REPEAT_MINTS_MIN": 3,          # Минимальное количество повторений минта на одном аккаунте
    "REPEAT_MINTS_MAX": 6,          # Максимальное количество повторений минта на одном аккаунте
    "PROXIES": True,                # Использовать прокси или нет (Для СНГ стран прокси обязательно юзать, иначе РПС блок. Можно 1 штуку на все акки)
    "SHUFFLE_WALLETS": True         # Перемешать кошельки или нет
}

# Кошелек будет брать рандомную нфт из этого списка, не трогаем.
CONTRACTS_AND_QUANTITIES = [
    {"address": "0x4de73D198598C3B4942E95657a12cBc399E4aDB5", "quantity": 1},
    {"address": "0x53cb0B849491590CaB2cc44AF8c20e68e21fc36D", "quantity": 3},
    {"address": "0xca5F4088c11B51c5D2B9FE5e5Bc11F1aff2C4dA7", "quantity": 2},
    {"address": "0x266b7E8Df0368Dd4006bE5469DD4EE13EA53d3a4", "quantity": 3},
    {"address": "0x9eAE90902a68584E93a83D7638D3a95ac67FC446", "quantity": 3},
    {"address": "0x4073a52A3fc328D489534Ab908347eC1FcB18f7f", "quantity": 3},
    {"address": "0x12B93dA6865B035AE7151067C8d264Af2ae4be8E", "quantity": 10},
    {"address": "0x266b7E8Df0368Dd4006bE5469DD4EE13EA53d3a4", "quantity": 3},
    {"address": "0xC47ADb3e5dC59FC3B41d92205ABa356830b44a93", "quantity": 2},
    {"address": "0x96a420b4c68d12324a66d78780D6d3f1305358f8", "quantity": 3},
    {"address": "0x8A43793D26b5DBd5133b78A85b0DEF8fB8Fce9B3", "quantity": 99},
    {"address": "0xf8ec6596B7322b258a3aB490AA24faE28d929635", "quantity": 3},
    {"address": "0xA85B9F9154db5bd9C0b7F869bC910a98ba1b7A87", "quantity": 3},
    {"address": "0xbC2cA61440fAF65a9868295Efa5d5D87c55B9529", "quantity": 4},
    {"address": "0x8974B96dA5886Ed636962F66a6456DC39118A140", "quantity": 3}
]

# ---------------------- FUNCTIONS ----------------------

def initialize_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Подпишись - https://t.me/marcelkow_crypto\n\nConnected to RPC")

def load_files():
    with open('abi.json', 'r') as f:
        abi = json.load(f)
    with open('pkey.txt', 'r') as f:
        private_keys = [line.strip() for line in f]
    if CONFIG["SHUFFLE_WALLETS"]:
        random.shuffle(private_keys)
    proxies_list = []
    if CONFIG["PROXIES"]:
        with open('proxies.txt', 'r') as f:
            proxies_list = [line.strip() for line in f]
    return abi, private_keys, proxies_list

def initialize_session(proxies_list):
    session = requests.Session()
    if CONFIG["PROXIES"]:
        proxy_data = random.choice(proxies_list).split('@')
        credentials = proxy_data[0]
        ip_port = proxy_data[1]
        session.proxies = {
            "http": f"http://{credentials}@{ip_port}",
            "https": f"http://{credentials}@{ip_port}",
        }
    return session

def initialize_web3(session):
    w3 = Web3(HTTPProvider('https://rpc.zora.energy', session=session))
    if not w3.is_connected():
        logging.error("Not connected to RPC")
        exit()
    return w3

def check_file_exists():
    file_exists = os.path.isfile('transactions.csv')
    if not file_exists or os.stat('transactions.csv').st_size == 0:
        logging.warning("Файл transactions.csv пуст или не существует. Создание нового файла...")
        df = pd.DataFrame(columns=['Wallet', 'NFT', 'Contract', 'Transaction', 'Status'])
        df.to_csv('transactions.csv', index=False, encoding='utf-8-sig')
    else:
        df = pd.read_csv('transactions.csv', encoding='utf-8-sig')
    return df

def process_transactions(abi, private_keys, proxies_list, w3):
    df = check_file_exists()
    # Обработка каждого приватного ключа
    for index, private_key in enumerate(private_keys, 1):
        try:
            sender_address = w3.eth.account.from_key(private_key).address

            # Выбор случайного количества повторных транзакций минта
            repeat_mints = random.randint(CONFIG["REPEAT_MINTS_MIN"], CONFIG["REPEAT_MINTS_MAX"])
            ACCOUNT_DELAY = random.randint(CONFIG["ACCOUNT_DELAY_MIN"], CONFIG["ACCOUNT_DELAY_MAX"])

            for repeat_index in range(repeat_mints):
                # Выбор случайного контракта
                contract_and_quantity = random.choice(CONTRACTS_AND_QUANTITIES)
                contract_address = contract_and_quantity["address"]
                quantity_to_mint = contract_and_quantity["quantity"]

                # Инициализация контракта
                contract = w3.eth.contract(address=contract_address, abi=abi)
                mint_function = contract.functions.mint(quantity_to_mint)
                transaction_data = mint_function._encode_transaction_data()

                # Получение имени токена
                token_name = contract.functions.name().call()

                estimated_gas = w3.eth.estimate_gas({
                    'to': contract_address,
                    'from': sender_address,
                    'data': transaction_data
                })

                # Создание объекта транзакции
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

                # Подписание и отправка транзакции
                signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
                txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

                # Ожидание завершения транзакции
                receipt = w3.eth.wait_for_transaction_receipt(txn_hash)

                # Проверка статуса транзакции и запись в CSV
                status = "Success" if receipt.status == 1 else "Error"

                # Добавление данных в DataFrame и сохранение в CSV
                new_data = {'Wallet': sender_address, 'NFT': token_name, 'Contract': contract_address,
                            'Transaction': f"https://explorer.zora.energy/tx/{txn_hash.hex()}", 'Status': status}
                df = df._append(new_data, ignore_index=True)
                df.to_csv('transactions.csv', index=False, encoding='utf-8-sig')

                # Вывод информации о транзакции
                checksum_address = w3.to_checksum_address(sender_address)
                logging.info(
                    f"Сейчас работаю с кошельком [{index}/{len(private_keys)}]\n"
                    f"Кошелек: {checksum_address} минтит {token_name}")
                logging.info(f"Количество повторений для этого кошелька: [{repeat_index + 1}/{repeat_mints}]")
                if receipt.status == 1:
                    logging.info(f"Транзакция успешно выполнена: https://explorer.zora.energy/tx/{txn_hash.hex()}")
                else:
                    logging.warning(f"Транзакция была отклонена: https://explorer.zora.energy/tx/{txn_hash.hex()}")
                DELAY = random.randint(CONFIG["DELAY_MIN"], CONFIG["DELAY_MAX"])
                logging.info(f"Задержка между транзакциями: {DELAY} секунд")
                logging.info('-' * 50)
                for _ in tqdm(range(DELAY), desc="Задержка между транзакциями", ncols=100):
                    time.sleep(1)
                logging.info('-' * 50)

            logging.info(f"Задержка между кошельками: {ACCOUNT_DELAY} секунд")
            logging.info('-' * 50)
            for _ in tqdm(range(ACCOUNT_DELAY), desc="Задержка между аккаунтами", ncols=100):
                time.sleep(1)
            logging.info('-' * 50)

        except Exception as e:
            logging.error(f"Ошибка при обработке кошелька {sender_address} с контрактом {contract_address}. {e}\n"
                          + '-' * 50)
            error_data = {'Wallet': sender_address, 'NFT': token_name, 'Contract': contract_address,
                          'Transaction': str(e), 'Status': "Error"}
            df = df._append(error_data, ignore_index=True)
            df.to_csv('transactions.csv', index=False, encoding='utf-8-sig')

# ---------------------- MAIN EXECUTION ----------------------

if __name__ == "__main__":
    initialize_logging()
    abi, private_keys, proxies_list = load_files()
    session = initialize_session(proxies_list)
    w3 = initialize_web3(session)
    process_transactions(abi, private_keys, proxies_list, w3)
