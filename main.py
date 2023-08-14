import requests
from web3 import Web3, HTTPProvider
import json
import time
import random
import csv

# Настройки
DELAY_MIN = 30                              # Рандомная задержка между транзакциями ОТ
DELAY_MAX = 100                             # Рандомная задержка между транзакциями ДО
ACCOUNT_DELAY = random.randint(600, 900)    # Задержка между разными кошельками
REPEAT_MINTS_MIN = 3                        # Минимальное количество повторений минта на одном аккаунте
REPEAT_MINTS_MAX = 9                        # Максимальное количество повторений минта на одном аккаунте
PROXIES = True                              # Использовать прокси или нет (Для СНГ стран прокси обязательно юзать, иначе РПС блок. Можно 1 штуку на все акки)
SHUFFLE_WALLETS = True                      # Перемешать кошельки или нет

# Один кошелек будет брать рандомную нфт из этого контракта, не трогаем.
CONTRACTS_AND_QUANTITIES = [
    {"address": "0x4de73D198598C3B4942E95657a12cBc399E4aDB5", "quantity": 1},
    {"address": "0x53cb0B849491590CaB2cc44AF8c20e68e21fc36D", "quantity": 3},
    {"address": "0xca5F4088c11B51c5D2B9FE5e5Bc11F1aff2C4dA7", "quantity": 2}

]

# Загрузка ABI контракта
with open('abi.json', 'r') as f:
    abi = json.load(f)

# Загрузка приватных ключей
with open('pkey.txt', 'r') as f:
    private_keys = [line.strip() for line in f]

# Если нужно перемешать кошельки
if SHUFFLE_WALLETS:
    random.shuffle(private_keys)

# Загрузка списка прокси
if PROXIES:
    with open('proxies.txt', 'r') as f:
        proxies_list = [line.strip() for line in f]

# Инициализация сессии requests с прокси или без
session = requests.Session()

if PROXIES:
    proxy_data = random.choice(proxies_list).split('@')
    credentials = proxy_data[0]
    ip_port = proxy_data[1]
    session.proxies = {
        "http": f"http://{credentials}@{ip_port}",
        "https": f"http://{credentials}@{ip_port}",
    }

# Инициализация подключения к Zora
w3 = Web3(HTTPProvider('https://rpc.zora.energy', session=session))

if not w3.is_connected():
    print("Not connected to RPC")
    exit()

print("Connected to RPC")

# Создание CSV файла для записи результатов
with open('transactions.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['Кошелек', 'Адрес контракта', 'Ссылка на транзакцию', 'Статус'])

# Обработка каждого приватного ключа
for index, private_key in enumerate(private_keys, 1):
    try:
        sender_address = w3.eth.account.from_key(private_key).address

        # Выбор случайного контракта
        contract_and_quantity = random.choice(CONTRACTS_AND_QUANTITIES)
        contract_address = contract_and_quantity["address"]
        quantity_to_mint = contract_and_quantity["quantity"]

        # Инициализация контракта
        contract = w3.eth.contract(address=contract_address, abi=abi)
        mint_function = contract.functions.mint(quantity_to_mint)
        transaction_data = mint_function._encode_transaction_data()

        # Выбор случайного количества повторных транзакций минта
        repeat_mints = random.randint(REPEAT_MINTS_MIN, REPEAT_MINTS_MAX)
        for repeat_index in range(repeat_mints):
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
            status = "Успешно" if receipt.status == 1 else "Неуспешно"
            with open('transactions.csv', 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(
                    [sender_address, contract_address, f"https://explorer.zora.energy/tx/{txn_hash.hex()}", status])

            # Вывод информации о транзакции
            checksum_address = w3.to_checksum_address(sender_address)
            print(f"Кошелек: {checksum_address} [{index}/{len(private_keys)}]")
            print(f"Количество повторений для этого кошелька: [{repeat_index + 1}/{repeat_mints}]")
            if receipt.status == 1:
                print(f"Транзакция успешно выполнена: https://explorer.zora.energy/tx/{txn_hash.hex()}")
            else:
                print(f"Транзакция была отклонена: https://explorer.zora.energy/tx/{txn_hash.hex()}")
            DELAY = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"Задержка между транзакциями: {DELAY} секунд\n" + '-' * 20)
            time.sleep(DELAY)
        print(f"Задержка между кошельками: {ACCOUNT_DELAY} секунд\n" + '-' * 20)
        time.sleep(ACCOUNT_DELAY)

    except Exception as e:
        print(f"Ошибка при обработке кошелька {sender_address}: {e}")
