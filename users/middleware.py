# # middleware.py
# from django.utils import timezone



# class UpdateLastSeenMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         print('Called')
#         if request.user.is_authenticated:
#             print('Yeah Executing')
#             print(request.user.last_seen)
#             request.user.last_seen = timezone.now()
#             request.user.save(update_fields=["last_seen"])
#             print(request.user.last_seen)
#         return self.get_response(request)
