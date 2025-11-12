from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User, PasswordResetToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth import get_user_model
from .models import LoginAttempt, UserProfile, RiderProfile, Referral
from django.contrib.auth import authenticate
from .tasks import save_profile_picture, save_rider_profile_picture
from rest_framework.response import Response




User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)


    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'password', 'password2','fullname','user_type', 'referral_code')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    

    def create(self, validated_data, **kwargs):
        validated_data.pop('password2')
        secret = kwargs.get('secret')
        print(secret)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number = validated_data['phone_number'],
            fullname=validated_data['fullname'],
            user_type=validated_data['user_type']
        )
        return user



class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields.pop('username', None)

    def validate(self, attrs):
        # Use Django's authenticate to handle user validation
        credentials = {
            'email': attrs.get('email'),
            'password': attrs.get('password')
        }
        user = authenticate(**credentials)
        
        if user is None:
            raise serializers.ValidationError('Invalid credentials', code='authentication')

        # Generate token and add custom claims
        refresh = self.get_token(user)
        return {
            'id': str(user.id),
            'username': user.username,
            'usertype': user.user_type,
            'token': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['user_type'] = user.user_type
        return token


class ActivateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10) 
    
    
class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id','username', 'fullname', 'phone_number', 'referral_code')
        

class RiderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    fullname = serializers.CharField(source='user.fullname', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    address = serializers.CharField(required=False)
    profile_picture = serializers.ImageField(required=False)
    
    class Meta:
        model = RiderProfile
        fields = ['username', 'fullname', 'phone_number', 'address', 'profile_picture']
        
        
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        instance.address = validated_data.get('address', instance.address)
        profile_picture = validated_data.pop('profile_picture', None)
        instance.save()
        

        
        if user_data:
            print(True)
            user = instance.user
            model_fields = {f.name for f in user._meta.get_fields()}
            for attr, value in user_data.items():
                if attr in model_fields:
                    print(attr, value)
                    setattr(user, attr, value)
            user.save()
            
        if profile_picture:
            # Get raw file bytes and name
            file_data = profile_picture.read()
            file_name = profile_picture.name
            save_rider_profile_picture.delay(instance.id, file_data, file_name),
            
        instance.refresh_from_db()
        instance.user.refresh_from_db()
        return instance



class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    fullname = serializers.CharField(source='user.fullname', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    referral_code = serializers.CharField(source='user.referral_code', required=False)
    address = serializers.CharField(required=False)
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = ['username', 'fullname', 'phone_number', 'address', 'profile_picture', 'referral_code']
        
        
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        instance.address = validated_data.get('address', instance.address)
        profile_picture = validated_data.pop('profile_picture', None)
        instance.save()
        
        try:
            from .utils.redis_cli import redis_client
            cache_key = f"user_profile:{instance.user.id}"
            print(cache_key)
            redis_client.delete(cache_key)
        except Exception as e:
            # Optionally log this error
            print(f"Failed to invalidate Redis cache: {str(e)}")

        
        if user_data:
            print(True)
            user = instance.user
            model_fields = {f.name for f in user._meta.get_fields()}
            for attr, value in user_data.items():
                if attr in model_fields:
                    print(attr, value)
                    setattr(user, attr, value)
            user.save()
     
        if profile_picture:
            # Get raw file bytes and name
            file_data = profile_picture.read()
            file_name = profile_picture.name
            save_profile_picture.delay(instance.id, file_data, file_name),
            
        instance.refresh_from_db()
        instance.user.refresh_from_db()
        return instance


class ReferralSerializer(serializers.ModelSerializer):
    # referrer = UserSerializer()
    # referred_user = UserSerializer()
    class Meta:
        model = Referral
        fields = '__all__'
        
        
        
from rest_framework import serializers
from .models import Rating



class RateMovbaySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Rating
        fields = '__all__'