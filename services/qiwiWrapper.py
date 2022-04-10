import requests
from config import *
from services.bdWrapper import *

def get_last_payments():
    payments = []
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + QIWI_TOKEN
    h = s.get('https://edge.qiwi.com/payment-history/v2/persons/' + QIWI_LOGIN + '/payments?rows=10')
    for payment in h.json()['data']:
        if payment["sum"]["currency"] == 643 and payment["errorCode"] == 0:
            payments.append([payment["sum"]["amount"], payment["comment"], payment["txnId"]])
    return payments

def check_pay(order_id):
    payments = get_last_payments()
    order = get_order_by_id(order_id)
    for payment in payments:
        if payment[1] == str(order_id) and not hash_presence(payment[2]) and payment[0] == order[4]:
            change_order_parametr(order_id, "hash", payment[2])
            return True
    return False