import qrcode
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from io import BytesIO
import uuid
from .models import Order, Scan
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from .utils.helper import generate_manual_code


class GenerateQRCodeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    

    def post(self, request):
        order_id = request.data.get('order_id')
        qr_data = f"delivery-{order_id}"
        manual_code = generate_manual_code()

        # Create or get order
        order, created = Order.objects.get_or_create(
            user=request.user,
            order_id=order_id,
        )

        # Create QR code metadata
        Scan.objects.create(order=order, qr_data=qr_data, manual_code=manual_code)

        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Return QR code image and manual code
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="image/png")
        response['X-Manual-Code'] = manual_code
        return response

class ScanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scan_data = request.data.get('scan_data')
        manual_code = request.data.get('manual_code')

        if not (scan_data or manual_code):
            return Response(
                {'error': 'No scan data or manual code provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check if either qr_data or manual_code matches a valid scan
            if scan_data:
                scan_record = Scan.objects.get(qr_data=scan_data, is_valid=True)
            else:
                scan_record = Scan.objects.get(manual_code=manual_code, is_valid=True)

            order = scan_record.order

            # Mark order as delivered
            order.is_delivered = True
            order.delivered_at = timezone.now()
            order.save()

            # Invalidate QR code and manual code
            scan_record.is_valid = False
            scan_record.save()

            return Response(
                {'message': 'Delivery confirmed', 'order_id': order.order_id},
                status=status.HTTP_200_OK
            )
        except Scan.DoesNotExist:
            return Response(
                {'error': 'Invalid or already used QR code/manual code'},
                status=status.HTTP_400_BAD_REQUEST
            )