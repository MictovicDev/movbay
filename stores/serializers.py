from rest_framework import serializers
from .models import (Store,
                     Order,
                     Delivery,
                     Product,
                     Status,
                     ProductImage)

from .tasks import upload_single_image
from base64 import b64encode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer



class StoreSerializer(serializers.ModelSerializer):
    # cac = serializers.ImageField()
    nin = serializers.ImageField()
    product_count = serializers.IntegerField(read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Store
        fields =  ('name', 'category', 'description','product_count', 'order_count','address1','followers_count', 'address2', 'cac', 'nin')

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
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("This field only accepts image files (jpg, png, gif, etc).")
        
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
                raise serializers.ValidationError("File extension not supported. Allowed: jpg, jpeg, png, gif.")
            return value
        else:
            return value
        

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        validated_data['owner'] = user
        return Store.objects.create(**validated_data)
       





class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url']


class ProductSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    images = serializers.ListField(required=True, write_only=True)
    product_images = ProductImageSerializer(many=True, required=False)
    
    class Meta:
        model = Product
        exclude = ['store']
        
    def upload_images(images, product_id):
        pass
        
          
    def create(self, validated_data):
        user = self.context['request'].user 
        
        images = validated_data.pop('images', [])
        post_to_story = validated_data.pop('auto_post_to_story', False) 
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
            print("TASK DISPATCHED:", res.id)
        if post_to_story:
           Status.objects.create(store=store, image=images[0])
        return product
 
 

class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = '__all__'
        


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    class Meta:
        model = Order
        fields = ['product', 'user', 'delivery', 'status']
        

    def create(self, validated_data):
        delivery_data = validated_data.pop('delivery')
        delivery = Delivery.objects.create(**delivery_data)
        order = Order.objects.create(delivery=delivery, **validated_data)
        return order

