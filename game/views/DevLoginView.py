from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class DevLoginView(APIView):
    authentication_classes = []  # allow unauthenticated access
    permission_classes = []  # dev only

    def post(self, request):
        username = request.data.get("username")
        if not username:
            return Response({"error": "username required"}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "user not found"}, status=404)

        login(request, user)  # sets session cookie
        return Response({"status": "logged_in", "username": username}, status=200)
