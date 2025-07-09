from rest_framework import serializers
from .models import (Store,
                     Order,
                     Delivery,
                     Product,
                     Status,
                     ProductImage,
                     StoreFollow,
                     OrderItem,
                     )

from .tasks import upload_single_image, upload_store_files, upload_video
from base64 import b64encode
from rest_framework.response import Response
from rest_framework import status
from users.serializers import UserSerializer, UserProfileSerializer


class StoreFollowSerializer(serializers.ModelSerializer):
    follower = UserSerializer()

    class Meta:
        model = StoreFollow
        fields = ('id', 'following', 'follower')


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


class StoreSerializer(serializers.ModelSerializer):
    cac = serializers.FileField()
    nin = serializers.FileField()
    store_image = serializers.ImageField()
    statuses = StatusSerializer(many=True)
    owner = UserSerializer()

    class Meta:
        model = Store
        fields = ('name', 'category', 'description', 'address1',
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
                cac = validated_data.pop('cac')
                nin = validated_data.pop('nin')
                store_image = validated_data.pop('store_image')
                files = {
                    "cac": cac.read(),
                    "nin": nin.read(),
                    "store_image": store_image.read()
                }
                validated_data['owner'] = user
                try:
                    store = Store.objects.create(**validated_data)
                except Exception as e:
                    raise e
                upload_store_files.delay(store.id, files)
                return store
            else:
                return Response({"Message": "User is not Authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            raise e


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url']


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
        print(store, validated_data)
        product = Product.objects.create(store=store, **validated_data)

        for image in images:
            image_data = {
                "file_content": b64encode(image.read()).decode("utf-8"),
                "filename": image.name,
                "product_id": product.id
            }
            res = upload_single_image.delay(image_data)
        video = b64encode(product_video.read()).decode('utf-8')
        upload_video.delay(video, product.id)
        if post_to_story:
            Status.objects.create(store=store, image=images[0])
        return product


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['product', 'amount', 'count']


class DeliverySerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Delivery
        fields = ['delivery_method', 'fullname', 'phone_number', 'email', 'user',
                  'delivery_address', 'alternative_address', 'landmark', 'city', 'state', 'postal_code']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(read_only=True, many=True)
    status = serializers.CharField(read_only=True)
    delivery = DeliverySerializer()
    buyer = UserSerializer()
    store = StoreSerializer()

    class Meta:
        model = Order
        fields = ['status', 'order_items', 'delivery', 'buyer', 'order_id', 'store']
        
        
    


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
