from django.contrib import admin
from .models import ChatBox, Message


admin.site.register(ChatBox)
admin.site.register(Message)

# @admin.register(ChatBox)
# class ChatBoxAdmin(admin.ModelAdmin):
#     list_display = ('id', 'sender', 'receiver', 'product', 'created_at')
#     search_fields = ('sender__fullname', 'receiver__fullname')
#     list_filter = ('created_at',)


# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('id', 'chatbox', 'sender', 'receiver', 'created_at', 'content')
#     search_fields = ('sender__fullname', 'receiver__fullname', 'content')
#     list_filter = ('chatbox', 'created_at')
