from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User, PasswordResetToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth import get_user_model
from .models import LoginAttempt, UserProfile


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)  # Confirm password

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'password', 'password2','fullname','user_type')

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
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to token
        token['email'] = user.email
        token['user_type'] = user.user_type
        return token
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields.pop('username', None)

        
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Check for too many failed attempts
        if LoginAttempt.check_failed_attempts(email):
            raise serializers.ValidationError(
                {"error": "Too many failed login attempts. Please try again later."}
            )

        # Validate credentials
        data = super().validate(attrs)

        # Log successful login
        ip_address = self.context['request'].META.get('REMOTE_ADDR')
        LoginAttempt.objects.create(email=email, success=True, ip_address=ip_address)
        
        return {
            "id": str(self.user.id),
            "username": self.user.username,
            "usertype": self.user.user_type,
            "token": {
                "access": data["access"],
                "refresh": data["refresh"],
            },
        }
    
    @classmethod
    def get_token(cls, user):
        token = RefreshToken.for_user(user)
        return token


class ActivateAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10) 
    
    
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'fullname', 'phone_number')



class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    fullname = serializers.CharField(source='user.fullname', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    address = serializers.CharField(required=False)
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = ['username', 'fullname', 'phone_number', 'address', 'profile_picture']
        
        
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        # Update user profile fields
        instance.address = validated_data.get('address', instance.address)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.save()

        # Update nested user fields
        if user_data:
            user = instance.user  # assuming UserProfile has OneToOneField to User
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        return instance
