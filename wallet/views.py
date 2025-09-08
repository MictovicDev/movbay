from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, WalletTransactions
from stores.models import Store
from .serializers import WalletSerializer, WalletTransactionSerializer
from rest_framework.response import Response
from rest_framework import status
from payment.factories import PaymentProviderFactory
from payment.utils.fees import calculate_withdrawal_fee
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from stores.permissions import IsAdminForPostOnly


class WalletDetailView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wallet = Wallet.objects.get(owner=request.user)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApproveWithdrawal(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminForPostOnly]

    def post(self, request, pk):
        
        provider_name = request.data.get('provider_name')
        try:
            provider = PaymentProviderFactory.create_provider(
                provider_name=provider_name)
        except Exception as e:
            return Response({"error": f"Invalid provider: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            withdrawal = get_object_or_404(
                WalletTransactions, pk=pk, type='Withdrawal', completed=False)
            transaction_code = withdrawal.transaction_code
            finalize_payload = {
                "transfer_code": transaction_code,
                "otp": request.data.get('otp')
            }
            transfer_response = provider.finalize_transfer(finalize_payload)
            print(transfer_response)
            if transfer_response.get('status') is True:
                withdrawal.wallet.balance -= withdrawal.amount
                withdrawal.wallet.total_withdrawal += withdrawal.amount
                withdrawal.completed = True
                withdrawal.status = 'completed'
                withdrawal.save()
            return Response(transfer_response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Finalization failed: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)



class DeclineWithdrawal(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pass


class Withdrawal(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            sent_amount = request.data.get('amount')

            if not sent_amount:
                return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                calculated_amount_data = calculate_withdrawal_fee(
                    float(sent_amount))
                calculated_amount = calculated_amount_data.get('final_payout')
            except (ValueError, TypeError):
                return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

            if user.wallet.balance < calculated_amount:
                return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

            provider_name = request.data.get('provider_name')
            if not provider_name:
                return Response({"error": "Provider name is required"}, status=status.HTTP_400_BAD_REQUEST)

            payload = {
                'account_number': request.data.get('account_number'),
                'bank_code': request.data.get('bank_code'),
            }

            if not payload['account_number'] or not payload['bank_code']:
                return Response({"error": "Account number and bank code are required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                provider = PaymentProviderFactory.create_provider(
                    provider_name=provider_name)
            except Exception as e:
                return Response({"error": f"Invalid provider: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                response = provider.verify_account(payload)
            except Exception as e:
                return Response({"error": f"Verification failed: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

            if response.get('status') is True:
                payload['account_name'] = response.get(
                    'data', {}).get('account_name')
                payload['type'] = "nuban"
                payload['currency'] = "NGN"

                try:
                    if user.wallet.reference_code and user.wallet.recipient_code:
                        data = {
                            "source": "balance",
                            "amount": calculated_amount * 100,
                            "recipient": user.wallet.recipient_code,
                            "reason": "Wallet withdrawal"
                        }
                        transfer_response = provider.transfer(data)
                        print(transfer_response)
                        WalletTransactions.objects.create(
                            wallet=user.wallet,
                            type='Withdrawal',
                            status='pending',
                            content=f"Withdrawal of {calculated_amount} to {payload['account_number']} at {payload['bank_code']}",
                            amount=calculated_amount,
                            transaction_code=transfer_response.get(
                                'data', {}).get('transfer_code'),
                            transaction_id=transfer_response.get(
                                'data', {}).get('id'),
                            reference_code=transfer_response.get(
                                'data', {}).get('reference')
                        )
                    else:
                        recipient_response = provider.create_transfer_recipient(
                            payload)
                        recipient_code = recipient_response.get(
                            'data', {}).get('recipient_code')
                        if not recipient_code:
                            return Response({"error": "Failed to create transfer recipient"}, status=status.HTTP_502_BAD_GATEWAY)

                        # Save recipient_code to wallet for next time
                        user.wallet.recipient_code = recipient_code
                        user.wallet.reference_code = recipient_code
                        user.wallet.save()

                        data = {
                            "source": "balance",
                            "amount": calculated_amount * 100,
                            "recipient": recipient_code,
                            "reason": "Wallet withdrawal"
                        }
                        transfer_response = provider.transfer(data)
                        print(transfer_response)
                        WalletTransactions.objects.create(
                            wallet=user.wallet,
                            type='Withdrawal',
                            status='pending',
                            content=f"Withdrawal of {calculated_amount} to {payload['account_number']} at {payload['bank_code']}",
                            amount=calculated_amount,
                            transaction_code=transfer_response.get(
                                'data', {}).get('transfer_code'),
                            transaction_id=transfer_response.get(
                                'data', {}).get('id'),
                            reference_code=transfer_response.get(
                                'data', {}).get('reference')
                        )
                    return Response({"Message": "Withdrawal has been placed"}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({"error": f"Transfer error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

            else:
                return Response({"error": "Invalid account number"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionHistory(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet = get_object_or_404(Wallet, owner=user)
        wallet_transactions = WalletTransactions.objects.filter(
            wallet=wallet).order_by('-created_at')
        paginator = PageNumberPagination()
        paginator.page_size = 5  # items per page
        result_page = paginator.paginate_queryset(wallet_transactions, request)

        # Serialize the paginated data
        serializer = WalletTransactionSerializer(result_page, many=True)

        # Return paginated response
        return paginator.get_paginated_response(serializer.data)
