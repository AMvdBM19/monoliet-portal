"""
Custom permission classes for the Monoliet Client Portal API.

These permissions ensure that:
- Admin users have full access to all resources
- Client users can only access their own data
- Sensitive information is protected from client users
"""

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission class that only allows admin users to access the resource.

    Admin users are identified by the is_staff flag on the User model.
    """

    def has_permission(self, request, view):
        """Check if the user is an admin."""
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsClientOwner(permissions.BasePermission):
    """
    Permission class that allows users to only access their own client's data.

    This permission checks if the user has a ClientProfile and if the
    requested object belongs to their client.
    """

    def has_permission(self, request, view):
        """Check if the user has a client profile."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if the user owns the object.

        For admin users: Always allow access
        For client users: Only allow if object belongs to their client
        """
        # Admin users can access everything
        if request.user.is_staff:
            return True

        # Check if user has a client profile
        if not hasattr(request.user, 'client_profile'):
            return False

        client_profile = request.user.client_profile
        if not client_profile.client:
            return False

        # Check object ownership based on object type
        if hasattr(obj, 'client'):
            # Object has a direct client relationship
            return obj.client == client_profile.client
        elif hasattr(obj, 'client_profile'):
            # For ClientProfile objects
            return obj == client_profile
        elif obj.__class__.__name__ == 'Client':
            # The object itself is a Client
            return obj == client_profile.client
        elif obj.__class__.__name__ == 'User':
            # The object is a User
            return obj == request.user

        return False


class IsClientUser(permissions.BasePermission):
    """
    Permission class that ensures the user is linked to a client.

    This is useful for views where we need to ensure the user has
    an associated client, regardless of which specific client data
    they're accessing.
    """

    def has_permission(self, request, view):
        """Check if the user has a client profile with an associated client."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin users always pass
        if request.user.is_staff:
            return True

        # Check if user has a client profile with a client
        if hasattr(request.user, 'client_profile'):
            return request.user.client_profile.client is not None

        return False


class ReadOnly(permissions.BasePermission):
    """
    Permission class that only allows read-only access (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        """Only allow safe methods."""
        return request.method in permissions.SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows:
    - Read-only access for authenticated users
    - Write access only for admin users
    """

    def has_permission(self, request, view):
        """Check permissions based on request method."""
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_staff


class CanCreateSupportTicket(permissions.BasePermission):
    """
    Permission class for support ticket creation.

    Both client users and admin users can create support tickets.
    """

    def has_permission(self, request, view):
        """Allow authenticated users to create tickets."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if the user can modify the ticket.

        Admins can modify all tickets.
        Client users can only view their own tickets (but not modify them).
        """
        if request.user.is_staff:
            return True

        if request.method in permissions.SAFE_METHODS:
            if hasattr(request.user, 'client_profile'):
                client_profile = request.user.client_profile
                if client_profile.client:
                    return obj.client == client_profile.client

        return False
