from rest_framework import serializers
from .models import (Store,
                     Order,
                     Delivery,
                     Product,
                     Status,
                     ProductImage,
                     StoreFollow
                     )

from .tasks import upload_single_image, create_cart, upload_store_files
from base64 import b64encode
from rest_framework.response import Response
from rest_framework import status
from users.serializers import UserSerializer




class StoreFollowSerializer(serializers.ModelSerializer):
     follower = UserSerializer()
     class Meta:
        model = StoreFollow
        fields =  ('id', 'following','follower')
    


class StoreSerializer(serializers.ModelSerializer):
    cac = serializers.FileField()
    nin = serializers.FileField()
    product_count = serializers.IntegerField(read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    store_image = serializers.ImageField()
    
    class Meta:
        model = Store
        fields =  ('name', 'category', 'description','product_count', 'order_count','address1','followers_count','store_image', 'address2', 'cac', 'nin')

    def validate_cac(self, value):
        if value:
            if value.content_type != 'application/pdf':
                raise serializers.ValidationError("The CAC document must be a PDF file.")
        
        # Alternatively, check file extension if content_type is not reliable
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError("The CAC document must have a .pdf extension.")
            
            # You can also check file size if needed, e.g. max 5MB
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError("The CAC document file size must be under 5MB.")
            return value
        else:
            return value
            
            
    def validate_nin(self, value):
        if value: 
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', 'pdf']
            if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
                raise serializers.ValidationError("File extension not supported. Allowed: jpg, jpeg, png, gif.")
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
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    images = serializers.ListField(required=True, write_only=True)
    product_images = ProductImageSerializer(many=True, required=False)
    
    class Meta:
        model = Product
        fields = '__all__'
        
    def upload_images(images, product_id):
        pass
        
          
    def create(self, validated_data):
        user = self.context['request'].user 
        
        images = validated_data.pop('images', [])
        post_to_story = validated_data.pop('auto_post_to_story', False)
        video = validated_data.pop('video', None)
        store = user.store
        product = Product.objects.create(store=store, **validated_data)
        
        for image in images:
            image_data = {
                "file_content": b64encode(image.read()).decode("utf-8"),
                "filename": image.name,
                "product_id": product.id
            }
            print(image.name)
            res = upload_single_image.delay(image_data)
            # res = upload_video.delay(video)
            print("TASK DISPATCHED:", res.id)
        if post_to_story:
           Status.objects.create(store=store, image=images[0])
        return product
 
 

class DeliverySerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Delivery
        fields = ['delivery_method','fullname', 'phone_number', 'email', 'user', 'delivery_address', 'alternative_address', 'landmark', 'city', 'state', 'postal_code']
        
    def create(self, validated_data):
        user = self.context['request'].user 
        validated_data['user'] = user
        delivery = Delivery.objects.create(**validated_data)
        return delivery
           
            

class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    class Meta:
        model = Order
        fields = ['product', 'user', 'delivery', 'status']
        

    def create(self, validated_data):
        delivery_data = validated_data.pop('delivery')
        pass
    
    
