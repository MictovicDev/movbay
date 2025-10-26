from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated




class RateMovbay(APIView):
    authentication_classes = [IsAuthenticated]
    
    
    def post(self, request):
        pass