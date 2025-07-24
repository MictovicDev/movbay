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
            
            
            
            
# ### Secure QR Code Upload & Access Flow in Django

# ---

# #### 1. Uploading Image to Cloudinary with Expiry Link

# **models.py**
# ```python
# import cloudinary
# import cloudinary.uploader
# import uuid
# from django.db import models

# class OrderCode(models.Model):
#     order_id = models.CharField(max_length=100)
#     qr_image = models.URLField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField()
#     token = models.CharField(max_length=255)  # Used for JWT-based access
# ```

# **utils.py**
# ```python
# import jwt
# import datetime
# from django.conf import settings

# SECRET_KEY = settings.SECRET_KEY


# def generate_qr_token(order_id, expiry_minutes=30):
#     payload = {
#         "order_id": order_id,
#         "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)
#     }
#     return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# def decode_qr_token(token):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         return payload
#     except jwt.ExpiredSignatureError:
#         return None
#     except jwt.InvalidTokenError:
#         return None
# ```

# **views.py**
# ```python
# from cloudinary.uploader import upload as cloud_upload
# from django.utils import timezone
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from .models import OrderCode
# from .utils import generate_qr_token

# class UploadQRView(APIView):
#     def post(self, request):
#         order_id = request.data.get("order_id")

#         # Upload a dummy image or real QR code
#         result = cloud_upload("path/to/generated_qr.png")
#         qr_url = result["secure_url"]

#         expires_at = timezone.now() + timezone.timedelta(minutes=30)
#         token = generate_qr_token(order_id)

#         qr_obj = OrderCode.objects.create(
#             order_id=order_id,
#             qr_image=qr_url,
#             expires_at=expires_at,
#             token=token
#         )

#         return Response({
#             "qr_token": token,
#             "expires_in": "30 minutes"
#         })
# ```

# ---

# #### 2. Client Requests Secure Access

# **views.py**
# ```python
# from rest_framework.permissions import AllowAny
# from .utils import decode_qr_token

# class GetQRImage(APIView):
#     permission_classes = [AllowAny]  # Authless, secured by token

#     def get(self, request):
#         token = request.query_params.get("token")
#         data = decode_qr_token(token)

#         if not data:
#             return Response({"error": "Invalid or expired token"}, status=400)

#         try:
#             code = OrderCode.objects.get(order_id=data["order_id"], token=token)
#         except OrderCode.DoesNotExist:
#             return Response({"error": "QR not found"}, status=404)

#         return Response({"qr_url": code.qr_image})
# ```

# Now the frontend can do:
# ```js
# GET /api/qr/get/?token=eyJhbGciOi...
# ```

# ---

# #### 3. Celery Job to Delete Expired QR Codes

# **tasks.py**
# ```python
# from celery import shared_task
# from django.utils import timezone
# from .models import OrderCode

# @shared_task
# def delete_expired_qrs():
#     expired = OrderCode.objects.filter(expires_at__lt=timezone.now())
#     for qr in expired:
#         # optionally delete from Cloudinary here too
#         qr.delete()
# ```

# **Celery beat**
# Schedule `delete_expired_qrs` to run every 10 minutes.

# ---

# #### 4. Seller's Scanner API

# **views.py**
# ```python
# from rest_framework.permissions import IsAuthenticated
# from .utils import decode_qr_token

# class ConfirmQRCode(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         token = request.data.get("token")
#         data = decode_qr_token(token)

#         if not data:
#             return Response({"error": "Invalid or expired QR code"}, status=400)

#         # Mark order as confirmed, or trigger logic
#         return Response({"status": "QR validated", "order_id": data['order_id']})
# ```

# ---

# Let me know if you want:
# - Cloudinary upload to generate and store actual QR images.
# - Admin tools to preview or manage QR codes.
# - Different expiry times per order type.
