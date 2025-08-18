from rest_framework import serializers
from .models import (Store,
                     Order,
                     Delivery,
                     Product,
                     Status,
                     ProductImage,
                     StoreFollow,
                     OrderItem,
                     OrderTracking
                     )
from .tasks import upload_store_files, upload_video, upload_image
from base64 import b64encode
from rest_framework.response import Response
from rest_framework import status
from users.serializers import UserSerializer
from users.serializers import UserProfileSerializer
from .utils.get_store_cordinate import get_coordinates_from_address
from logistics.models import KYC
from rest_framework import serializers
from .models import Review
from logistics.models import Ride
from users.utils.otp import OTPManager
# from logistics.serializers import RiderSerializer
from users.models import RiderProfile
from .models import ProductRating



class ClientStoresSerializer(serializers.ModelSerializer):
    store_image = serializers.ImageField()
    class Meta:
        model = Store
        fields = ('id','name', 'category', 'description', 'address1',
                  'store_image', 'address2','owner', 'store_image_url')
               

class StoreFollowSerializer(serializers.ModelSerializer):
    follower = UserProfileSerializer()
    # followed_store = ClientStoresSerializer(read_only=True)
    #followed_store = serializers.PrimaryKeyRelatedField(read_only=True)
    is_following_back = serializers.BooleanField(default=False)  # for followers endpoint
    they_follow_me_back = serializers.BooleanField(default=False)  # for following endpoint

    class Meta:
        model = StoreFollow
        fields = [
            'follower',
            'followed_store',
            'followed_at',
            'is_following_back',
            'they_follow_me_back'
        ]

        

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = '__all__'


class DashboardSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    store_image = serializers.ImageField()
    statuses = StatusSerializer(many=True)
    owner = UserSerializer()

    class Meta:
        model = Store
        fields = '__all__'



class StoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ('id','name', 'category', 'description', 'address1',
                  'store_image', 'address2', 'cac', 'nin', 'statuses', 'owner')
        
        
    def validate_cac(self, value):
        if value:
            # Alternatively, check file extension if content_type is not reliable
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError(
                    "The CAC document must have a .pdf extension.")

            # You can also check file size if needed, e.g. max 5MB
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    "The CAC document file size must be under 5MB.")
            return value
        else:
            return value

    def validate_nin(self, value):
        if value:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', 'pdf']
            if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
                raise serializers.ValidationError(
                    "File extension not supported. Allowed: jpg, jpeg, png, gif.")
            return value
        else:
            return value

    
class StoreSerializer(serializers.ModelSerializer):
    cac = serializers.FileField(required=False)
    nin = serializers.FileField(required=False)
    store_image = serializers.ImageField()
    statuses = StatusSerializer(many=True, required=False)
    owner = UserSerializer(required=False)

    class Meta:
        model = Store
        fields = ('id','name', 'category', 'description', 'address1',
                  'store_image', 'address2', 'cac', 'nin', 'statuses', 'owner')

    def validate_cac(self, value):
        if value:
            # Alternatively, check file extension if content_type is not reliable
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError(
                    "The CAC document must have a .pdf extension.")

            # You can also check file size if needed, e.g. max 5MB
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    "The CAC document file size must be under 5MB.")
            return value
        else:
            return value

    def validate_nin(self, value):
        if value:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', 'pdf']
            if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
                raise serializers.ValidationError(
                    "File extension not supported. Allowed: jpg, jpeg, png, gif.")
            return value
        else:
            return value

    def create(self, validated_data):
        request = self.context.get('request')
        try:
            if request.user.is_authenticated:
                user = request.user
                try:
                    cac = validated_data.pop('cac')
                    nin = validated_data.pop('nin')
                    store_image = validated_data.pop('store_image')
                except Exception as e:
                    print(str(e))
                otp_m = OTPManager()
                response = get_coordinates_from_address(validated_data.get('address1'))
                    
                try:
                    files = {
                    "cac": cac.read(),
                    "nin": nin.read(),
                    "store_image": store_image.read()
                }
                except Exception as e:
                    print(str(e))
                validated_data['owner'] = user
                try:
                    store = Store.objects.create(**validated_data)
                    if response:
                        store.latitude = response.get('latitude')
                        store.longitude = response.get('longitude')
                        store.save()
                except Exception as e:
                    raise e
                try:
                    upload_store_files.delay(store.id, files)
                except Exception as e:
                    print(str(e))
                return store
            else:
                return Response({"Message": "User is not Authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            raise e



class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url']


class VerifyOrderSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=5)


class ProductRatingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ProductRating
        fields = ['rating', 'comment', 'user']  # Only include fields the user should POST
        read_only_fields = ['id', 'user', 'product']

class UpdateProductSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(read_only=True)
    store = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    images = serializers.ListField(required=False, write_only=True)
    product_images = ProductImageSerializer(many=True, required=False, read_only=True)

    def __init__(self, *args, **kwargs):
        # make all fields optional (for partial updates)
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in self.Meta.read_only_fields:
                self.fields[field].required = False

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id', 'verified', 'store', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(read_only=True)
    store = StoreSerializer(read_only=True)
    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M", read_only=True)
    images = serializers.ListField(required=True, write_only=True)
    product_images = ProductImageSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = '__all__'

    def validate_product_video(self, value):
        if value:
            print(value.content_type)
            if value.content_type != 'video/mp4':
                raise serializers.ValidationError("Upload a Video file.")

            max_size = 200 * 1024 * 1024  # 50 MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    "Video file too large. Max size is 20MB.")
            return value
        else:
            raise serializers.ValidationError("No Video File")

    def upload_images(images, product_id):
        pass

    def create(self, validated_data):
        user = self.context['request'].user
        images = validated_data.pop('images', [])
        post_to_story = validated_data.pop('auto_post_to_story', False)
        product_video = validated_data.pop('product_video', None)
        store = user.store
        print(images)
        try:
            product = Product.objects.create(store=store, **validated_data)
        except Exception as e:
            print(str(e))
        serialized_images = [
        {
                "file_content": b64encode(image.read()).decode("utf-8"),
                "filename": image.name,
                "product_id": product.id
            }
            for image in images
        ]
        if serialized_images:
            res = upload_image.delay(serialized_images, product.id)
        if product_video:
            video = b64encode(product_video.read()).decode('utf-8')
            upload_video.delay(video, product.id)
        if post_to_story:
            Status.objects.create(store=store, image=images[0])
        return product


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(required=False)
    
    class Meta:
        model = OrderItem
        fields = ['product', 'amount', 'count']
  

class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = ['rider','vehicle_type', 'plate_number', 'vehicle_color']



class RiderProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    kyc_verification = KYCSerializer(read_only=True, many=True)
    
    class Meta:
        model = RiderProfile   
        fields = '__all__'
        
class OrderTrackingSerializer(serializers.ModelSerializer):
    driver = RiderProfileSerializer(read_only=True)
    
    class Meta:
        model = OrderTracking
        fields = '__all__'
    
    
class DeliverySerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Delivery
        fields = ['delivery_method', 'fullname', 'phone_number', 'email', 'user',
                  'delivery_address', 'alternative_address', 'landmark', 'city', 'state', 'postal_code']


class RideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = '__all__'




class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(read_only=True, many=True)
    status = serializers.CharField(read_only=True)
    delivery = DeliverySerializer()
    buyer = UserSerializer(read_only=True)
    store = StoreSerializer(read_only=True)
    ride = RideSerializer(read_only=True, many=True)

    class Meta:
        model = Order
        fields = ['status', 'order_items', 'delivery', 'buyer', 'order_id', 'store', 'assigned', 'ride']
        
        

class ItemSerializer(serializers.Serializer):
    store = serializers.IntegerField()
    product = serializers.IntegerField()
    amount = serializers.IntegerField()
    quantity = serializers.IntegerField()


class ShopSerializer(serializers.Serializer):
    delivery = DeliverySerializer()
    items = ItemSerializer(many=True)
    payment_method = serializers.CharField()
    provider_name = serializers.CharField()
    total_amount = serializers.IntegerField()


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    store = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'store', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
        
            
class ClientStoreSerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    store_image = serializers.ImageField()
    products = ProductSerializer(many=True)

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'description',
            'post_count', 'follower_count', 'following_count',
            'is_following', 'products', 'store_image', 'store_image_url','store_image'
        ]

    def get_post_count(self, obj):
        return obj.products.count()

    def get_follower_count(self, obj):
        return obj.store_followers.count()

    def get_following_count(self, obj):
        # assuming store owner can follow other stores
        return StoreFollow.objects.filter(follower=obj.owner.user_profile, followed_store__isnull=False).count()

    def get_is_following(self, obj):
        try:
            user = self.context['request'].user
            if user.is_authenticated:
                return StoreFollow.objects.filter(follower=user.user_profile, followed_store=obj).exists()
            return False
        except Exception as e:
            return Response(str(e), status=400)
    
    