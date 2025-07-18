from rest_framework import permissions

class IsProductOwner(permissions.BasePermission):
    """
    Custom permission to allow only the product owner to edit or delete it.
    """

    def haspermission(self, request, view, obj):
        if request.method == 'POST':
            return obj.store.owner == request.user
        


class IsStoreOwner(permissions.BasePermission):
    """
    Custom permission to only allow store owners to access orders that belong to their store.
    """

    def has_object_permission(self, request, view, obj):
        # obj here is expected to be an instance of Order
        return obj.store.owner == request.user
