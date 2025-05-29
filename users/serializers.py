from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User, PasswordResetToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth import get_user_model


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields.pop('username', None)
    
    def validate(self, attrs):
        data = super().validate(attrs)
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
