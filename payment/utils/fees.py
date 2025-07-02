# utils/fees.py

def calculate_purchase_fee(amount_naira):
    """
    Calculates Paystack and platform fee for funding transactions.
    Assumes amount is in Naira.
    """
    paystack_fee = int(amount_naira * 0.015)
    if amount_naira >= 2500:
        paystack_fee += 100
    paystack_fee = min(paystack_fee, 2000)

    platform_fee = int(amount_naira * 0.09)
    platform_fee += 100
    final_wallet_credit = amount_naira - paystack_fee - platform_fee

    return {
        "original_amount": amount_naira,
        "paystack_fee": paystack_fee,
        "platform_fee": platform_fee,
        "wallet_credit": final_wallet_credit
    }


def calculate_wallet_fee(amount_naira):
    """
    Calculates Paystack for funding transactions.
    Assumes amount is in Naira.
    """
    paystack_fee = int(amount_naira * 0.015)
    if amount_naira >= 2500:
        paystack_fee += 100
    paystack_fee = min(paystack_fee, 2000)
    final_wallet_credit = amount_naira - paystack_fee

    return {
        "original_amount": amount_naira,
        "paystack_fee": paystack_fee,
        "wallet_credit": final_wallet_credit
    }


def calculate_withdrawal_fee(amount_naira, plan_type="starter"):
    """
    Calculates Paystack transfer fee and your platform withdrawal fee.
    """
    paystack_fee = 10 if plan_type == "starter" else 0
    platform_fee = int(amount_naira * 0.005)  # 0.5% for example
    final_payout = amount_naira - paystack_fee - platform_fee

    return {
        "requested_withdrawal": amount_naira,
        "paystack_transfer_fee": paystack_fee,
        "platform_fee": platform_fee,
        "final_payout": final_payout
    }
