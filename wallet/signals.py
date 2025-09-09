from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from wallet.models import Wallet, WalletTransactions
import logging

# Configure logger if not already done
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Wallet)
def snapshot_wallet(sender, instance, **kwargs):
    """
    Store old values on the instance before saving.
    """
    if instance.pk:  # Only if the wallet already exists
        print(True)
        try:
            old_wallet = Wallet.objects.get(pk=instance.pk)
            # Attach old values to the instance temporarily
            instance._previous_balance = old_wallet.balance
            instance._previous_deposit = old_wallet.total_deposit
            instance._previous_withdrawal = old_wallet.total_withdrawal
        except Wallet.DoesNotExist:
            # This is a new wallet, so nothing to snapshot
            instance._previous_balance = instance.balance
            instance._previous_deposit = instance.total_deposit
            instance._previous_withdrawal = instance.total_withdrawal


@receiver(post_save, sender=Wallet)
def create_wallet_transactions(sender, instance, created, **kwargs):
    """
    Create WalletTransactions based on changes detected.
    """
    if created:
        return  # Skip for brand new wallets

    try:
        prev_balance = getattr(instance, "_previous_balance", instance.balance)
        prev_deposit = getattr(instance, "_previous_deposit", instance.total_deposit)
        prev_withdrawal = getattr(instance, "_previous_withdrawal", instance.total_withdrawal)

        if instance.total_deposit > prev_deposit:
            WalletTransactions.objects.create(
                wallet=instance,
                type='Account-Funded',
                amount=instance.total_deposit - prev_deposit,
                content=f"Wallet Funded. Previous Balance: {prev_balance}, New Balance: {instance.balance}",
                status='completed'
            )
            logger.info(f"Wallet funded for user {instance.owner.username}")

        elif instance.total_withdrawal > prev_withdrawal:
            WalletTransactions.objects.create(
                wallet=instance,
                type='Withdrawal',
                amount=instance.total_withdrawal - prev_withdrawal,
                content=f"Wallet Withdrawal. Previous Balance: {prev_balance}, New Balance: {instance.balance}",
                status='completed'
            )
            logger.info(f"Wallet withdrawal for user {instance.owner.username}")

    except Exception as e:
        logger.error(f"Error creating wallet transaction: {e}")
