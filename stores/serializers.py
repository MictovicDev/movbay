from rest_framework import serializers
from .models import (Store,
                     Order,
                     Delivery,
                     Product,
                     StoreStatus)

class StoreSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Store
        fields =  ('name', 'category', 'description', 'address1', 'address2', 'cac', 'nin')

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
       


class ProductSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    
    class Meta:
        model = Product
        exclude = ['store']
        # fields = '__all__'
          
    def create(self, validated_data):
        user = self.context['request'].user 
        store = user.store
        product = Product.objects.create(store=store, **validated_data)
        if validated_data['auto_post_to_story'] == True:
            StoreStatus.objects.create(store=store,
                                       content=validated_data['description'],
                                       image1=validated_data['image1'], 
                                       image2=validated_data['image2'],
                                       image3=validated_data['image3'])
        return product
 


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = '__all__'
        


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ['product', 'user', 'delivery']
        

    def create(self, validated_data):
        delivery_data = validated_data.pop('delivery')
        delivery = Delivery.objects.create(**delivery_data)
        order = Order.objects.create(delivery=delivery, **validated_data)
        return order

