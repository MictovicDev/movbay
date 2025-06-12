from rest_framework import permissions

class IsProductOwner(permissions.BasePermission):
    """
    Custom permission to allow only the product owner to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        return obj.store.owner == request.user