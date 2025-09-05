from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.validators import EmailValidator
import string
from stores.utils.helpers import user_file_path, validate_video_file_extension
import random
from django.db import models
from users.models import UserProfile
from cloudinary.models import CloudinaryField
from payment.models import Payment
from phonenumber_field.modelfields import PhoneNumberField
from users.models import RiderProfile

User = get_user_model()



class Store(models.Model):
    name = models.CharField(max_length=250, blank=True, null=True, db_index=True)
    category = models.CharField(max_length=250, blank=True, null=True, db_index=True)
    store_image = models.ImageField(upload_to='Store/PP', blank=True, null=True)
    description = models.TextField()
    owner = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, db_index=True, related_name='store')
    address1 = models.TextField()
    address2 = models.TextField()
    store_image = CloudinaryField('store/pp', blank=True, null=True)
    store_image_url = models.URLField(null=True)
    nin = CloudinaryField('store/nin', blank=True, null=True)
    nin_url = models.URLField(blank=True)
    cac = CloudinaryField('store/cac', blank=True, null=True)
    cac_url = models.URLField(null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True, default='NG')
    state = models.CharField(max_length=250 ,blank=True, null=True)
    verified = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name or 'Unnamed'} Store"

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['owner']),
        ]
        ordering = ['name']
  
  
class DeliveryOption(models.Model):
    DELIVERY_CHOICES = [
        ('Movbay_Express', 'Movbay_Express'),
        ('Speedy_Dispatch', 'Speedy_Dispatch'),
        ('Pickup', 'Pickup')
    ]
    name = models.CharField(max_length=50, choices=DELIVERY_CHOICES, unique=True)

    def __str__(self):
        return self.name
          

class Product(models.Model):
    
    CATEGORY = [
        ('Electronics', 'Electronics'),
        ('Fashion', 'Fashion'),
        ('Furniture', 'Furniture'),
        ('Beauty', 'Beauty'),
        ('Car', 'Car'),
        ('Sport', 'Sport'),
        ('Shoes', 'Shoes'),
        ('Bags', 'Bags'),
        ('Home & Garden', 'Home & Garden'),
        ('Books', 'Books'),
        ('Others', 'Others')
    ]
    
    PRODUCT_CONDITION = [
        ('New', 'New'),
        ('Used', 'Used'),
        ('Refurbished', 'Refurbished')
    ]
    
    
    #id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products', db_index=True)
    title = models.CharField(max_length=40, blank=True, null=True)
    category = models.CharField(max_length=250, blank=True, null=True)
    brand = models.CharField(max_length=250, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    product_video = models.FileField('videos', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    original_price = models.PositiveBigIntegerField(default=0)
    discounted_price = models.PositiveBigIntegerField(default=0)
    condition =  models.CharField(choices=PRODUCT_CONDITION, max_length=300, blank=True, null=True)
    verified = models.BooleanField(default=False, db_index=True)
    stock_available = models.IntegerField(default=1, blank=True, null=True)
    size = models.CharField(max_length=250, blank=True, null=True)
    pickup_available = models.BooleanField(default=True)
    delivery_available = models.BooleanField(default=True)
    movbay_express = models.BooleanField(default=False)
    speed_dispatch = models.BooleanField(default=False)
    pickup = models.BooleanField(default=False)
    # delivery_types = models.ManyToManyField(
    #     DeliveryOption,
    #     blank=True,
    #     related_name="products"
    # )
    auto_post_to_story = models.BooleanField(default=False)
    free_delivery = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.store.name if self.id else 'No Store'} - {self.id or 'Unnamed Product'}"

    class Meta:
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['verified']),
        ]
        ordering = ['-verified']



class ProductImage(models.Model):
    
    product = models.ForeignKey(Product, related_name='product_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='temp/', blank=True, null=True)
    image_url = models.URLField(blank=True)
    
    
    def __str__(self):
        return f"{self.product.title} - {self.image_url}"
                
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Users this profile is following
    following = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="followers",
        blank=True
    )

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
    


class ProductRating(models.Model):
    
    Rating = (
        ('1Star', '1Star'),
        ('2Star', '2Star'),
        ('3Star', '3Star'),
        ('4Star', '4Star'),
        ('5Star', '5Star'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    rating = models.CharField(max_length=250, choices=Rating)
    comment = models.TextField()
    
    
    def __str__(self):
        return f"{self.product} Rating"
   
 
class Review(models.Model):
    store = models.ForeignKey(Store, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()  # e.g., 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['store', 'user']  # One review per store per user
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.store.name} ({self.rating})"
    
    
 
class StoreFollow(models.Model):
    follower = models.ForeignKey(UserProfile, related_name='follows', on_delete=models.CASCADE, null=True)  # the user who follows
    followed_store = models.ForeignKey(Store, related_name='store_followers', null=True, blank=True, on_delete=models.CASCADE)
    followed_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'followed_store'], name='unique_store_follow'),
        ]

    def __str__(self):
        return f"{self.follower} follows store {self.followed_store.owner}"
        
    

class Status(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='statuses', db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True, blank=True, null=True)
    image = models.ImageField(upload_to='store/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ('store', 'product')
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['product']),
        ]

    def is_active(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"Status by {self.store} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)



# class StatusImage(models.Model):
#     image = models.ImageField(upload_to='store', blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     status = models.ForeignKey(Status, on_delete=models.CASCADE, blank=True, null=True, related_name='statusimages')
    
    
#     def __str__(self):
#         return f"Status image {self.status}"
                

def generate_order_id(size=8, prefix="MOV"):
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=size))
    return f"{prefix}{random_part}"


class Delivery(models.Model):
    DELIVERY_CHOICES = [
    ('movbay_dispatch', 'MovBay_Dispatch'),
    ('speedy_dispatch', 'Speedy_Dispatch'),
    ('pickup_hub', 'Pickup_Hub'),
    ]

    
    #id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_method = models.CharField(max_length=250, choices=DELIVERY_CHOICES)
    fullname = models.CharField(max_length=250, blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(
        validators=[EmailValidator(message="Enter a valid email address")]
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    delivery_address = models.TextField()
    landmark = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    state = models.CharField(max_length=250, blank=True, null=True)
    alternative_address = models.CharField(max_length=250, blank=True, null=True)
    alternative_name = models.CharField(max_length=250, blank=True, null=True)
    alternative_number = PhoneNumberField(region='NG', blank=True, null=True)
    alternative_email = models.EmailField(
        db_index=True,
        validators=[EmailValidator(message="Enter a valid email address")], blank=True, null=True
    )
    postal_code = models.PositiveBigIntegerField()
    courier_name = models.CharField(max_length=250, blank=True, null=True)
    tracking_number = models.CharField(max_length=250, blank=True, null=True)
    shiiping_amount = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    delivery_address_id = models.CharField(max_length=250, blank=True, null=True)
    pickup_address_id = models.CharField(max_length=250, blank=True, null=True)
    parcel_id = models.CharField(max_length=250, blank=True, null=True)

    # def __str__(self):
    #     return f"{self.user} Delivery" 

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'New Orders'),
        ('processing', 'Processing'),
        ('assigned', 'assigned'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='owner')
    confirmed = models.BooleanField(default=False)
    delivery = models.CharField(max_length=250, blank=True, null=True)
    delivery = models.ManyToManyField(Delivery)
    status = models.CharField(max_length=250, choices=STATUS_CHOICES, default='new')
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    amount = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    ride_accepted = models.BooleanField(default=False)
    assigned = models.BooleanField(default=False)
    out_for_delivery = models.BooleanField(default=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, blank=True, null=True)
    locked = models.BooleanField(default=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, blank=True, null=True, related_name='order')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    otp_secret = models.CharField(max_length=250, blank=True, null=True)
    code = models.CharField(max_length=250, null=True, blank=True)
    completed = models.BooleanField(default=False)
    
    
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            unique = False
            while not unique:
                new_id = generate_order_id()
                if not Order.objects.filter(order_id=new_id).exists():
                    unique = True
                    self.order_id = new_id
        super().save(*args, **kwargs)


    def __str__(self):
        return self.order_id

   
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True, related_name='order_items')
    count = models.PositiveIntegerField(default=1)
    amount = models.PositiveBigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True),
    
    
    
    def __str__(self):
        return f"{self.order} --> {self.count}"
   
   
   
class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_tracking')
    order_accepted = models.BooleanField(default=False)
    marked_for_delivery = models.BooleanField(default=False)
    item_picked = models.BooleanField(default=False)
    rider_en_route = models.BooleanField(default=False)
    arriving_soon = models.BooleanField(default=False, null=True)
    driver = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, blank=True, null=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.order.order_id
     

class OrderDispute(models.Model):
    
    issue = [
        ('Item_not_as_Described', 'Item_not_as_Described'),
        ('')
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    
    
   
class OrderHistory(models.Model):
    orderhistory = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    dispute = models.ForeignKey(OrderDispute, on_delete=models.CASCADE)
    
    
    def __str__(self):
        return self.order 