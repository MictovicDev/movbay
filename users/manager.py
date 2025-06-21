from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, username, email, phone_number, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            phone_number=phone_number,
            **extra_fields
        )
        
        user.set_password(password)
        # user.is_active = True
        user.save(using=self.db)
        return user
        
    def create_superuser(self, username, email, phone_number, password=None, **extra_fields):
        user = self.create_user(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
            **extra_fields
        )
        user.is_admin = True
        user.is_active = True
        user.is_superuser = True
        user.save(using=self.db)
        return user