from rest_framework.permissions import BasePermission

class IsStaffUser(BasePermission):
      """
      Custom permission to allow access only to hotel staff or admin
      """
      def has_permission(self,request,view):
            return bool(
                  request.user and
                  request.user.is_authenticated and
                  (request.user.is_staff or request.user.role in ['receptionist','manager'])
            )