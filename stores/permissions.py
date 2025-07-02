from rest_framework import permissions

class IsProductOwner(permissions.BasePermission):
    """
    Custom permission to allow only the product owner to edit or delete it.
    """

    def haspermission(self, request, view, obj):
        if request.method == 'POST':
            return obj.store.owner == request.user