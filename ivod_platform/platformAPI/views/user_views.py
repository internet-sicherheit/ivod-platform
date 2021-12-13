import sys
from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template import Engine
from django.template.loader import get_template
from django.template.response import SimpleTemplateResponse
from django.utils.decorators import method_decorator
from django.conf import settings

from ratelimit.decorators import ratelimit
from rest_framework import generics, permissions, serializers
from rest_framework.reverse import reverse
from ..serializers import UserSerializer
from ..util import send_verification_mail, render_to_string, send_a_mail
from ..models import User
from rest_framework import status
from rest_framework.response import Response
import threading

from django.core import signing
from django.core.exceptions import  ValidationError
from django.contrib.auth.password_validation import validate_password

class LoggedInUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, many=False, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class UserView(generics.RetrieveAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

class UserSearchView(generics.RetrieveAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()

    def get(self, request, *args, **kwargs):

        name = request.query_params["name"]

        def build_uuid_filter(id_query_input):
            # Check if input is a uuid. If input is not a uuid the whole lookup will fail with a ValidationError
            try:
                _ = UUID(id_query_input)
                return Q(id=id_query_input)  # Q(id=request.data["name"]) #direct lookup, should always work
            except Exception as e:
                # Empty query filter
                return Q()

        search_filter = (Q(is_verified=True) \
                         & (build_uuid_filter(name)  # Q(id=request.data["name"]) #direct lookup, should always work
                            | Q(public_profile=True)  # Otherwise only look for public profiles
                            & (
                                        Q(username__contains=name)  # Searching by username should work even if real name is hidden
                                        | (
                                                Q(real_name=True)  # Search by real name only when real name is publicly displayed
                                                & (
                                                        Q(first_name__contains=name)
                                                        | Q(last_name__contains=name))))))
        objects = User.objects.filter(search_filter)
        serializer = UserSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


class MultiUserView(generics.CreateAPIView):
    # permission_classes = [permissions.IsAuthenticated] #TODO: Filtering for hidden profiles/ sensitive user info?
    queryset = User.objects.all()

    # serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        objects = User.objects.filter(pk__in=request.data["users"])
        serializer = UserSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


@method_decorator(ratelimit(key='ip', rate='5/m'), name="dispatch")
class CreateUserView(generics.CreateAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        if type(request.user) == AnonymousUser:
            serializer = UserSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid(raise_exception=False):
                #Try to resend email
                if "email" in serializer.errors:
                    existing_user = User.objects.get(email=request.data["email"])
                    send_verification_mail(existing_user, request.data["email"], request)
                    return Response(status=status.HTTP_201_CREATED)
                else:
                    serializer.is_valid(raise_exception=True)
            else:
                self.perform_create(serializer)
                send_verification_mail(serializer.instance, request.data["email"], request)
                return Response(status=status.HTTP_201_CREATED)
        else:
            # TODO: Is there any legitimate reason to create another user while logged in?
            return Response(status=status.HTTP_403_FORBIDDEN)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class CreatePasswordResetRequest(generics.CreateAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):

        def passwordResetProcessing(email):
            try:
                # Get user with this email, if they exist. If they dont exist, there is nothing to do
                user = User.objects.get(email=email)
                serialized_id = signing.dumps({'user': user.id.hex, 'token_type': "PASSWORD_RESET"})
                target = request.build_absolute_uri(reverse("do_password_reset", kwargs={'reset_id': serialized_id}))

                # Get the URL that lets users reset their e-mail from the settings
                reset_url = getattr(settings, "PASSWORD_RESET_URL", None)
                if reset_url is None:
                    # if no URL is set in the settings, take default reset endpoint
                    reset_url = target
                else:
                    # Render token into the url
                    reset_url = render_to_string(Engine.get_default().from_string(reset_url),
                                                 context={'token': serialized_id, 'target': target}, request=request)

                # Build a reset mail from templates
                context = {
                    "reset_id": serialized_id,
                    "title": "Password Reset",
                    "reset_url": reset_url
                }
                text_content = render_to_string('platformAPI/mail_reset_text.jinja2', context=context, request=request)
                html_content = render_to_string('platformAPI/mail_reset_html.jinja2', context=context, request=request)
                # Dont send alternative when its an empty string
                if text_content == "":
                    text_content = None
                if html_content == "":
                    html_content = None

                # At least one message type must be specified
                if text_content is None and html_content is None:
                    # TODO: ValueError is too broad, use appropriate exception type instead
                    raise ValueError("Only empty templates where loaded")
                send_a_mail(email, context["title"], content=text_content, html_content=html_content)
            except User.DoesNotExist:
                pass

        if "email" in request.data:
            # Run in thread to avoid runtime oracle
            t = threading.Thread(target=passwordResetProcessing, args=(request.data["email"],), kwargs={})
            t.setDaemon(True)
            t.start()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ResetPasswordView(generics.ListCreateAPIView):
    serializer_class = serializers.Serializer

    def get(self, request, *args, **kwargs):
        # Simple password reset form. Replace the platformAPI/default_password_reset_page.jinja2 template to create your own form or change PASSWORD_RESET_URL to point to your frontend
        return SimpleTemplateResponse(get_template("platformAPI/default_password_reset_page.jinja2"),
                                      context={"reset_url": "_self", "reset_id": self.kwargs["reset_id"]}, status=200)

    def post(self, request, *args, **kwargs):
        try:
            token = self.kwargs["token"]
            # Load data from token and check expiration
            loadedObject = signing.loads(token, max_age=settings.TOKEN_MAX_LIFETIME)
            # Check if token type is a password reset token and not another signed by this server
            if "token_type" not in loadedObject or loadedObject["token_type"] != "PASSWORD_RESET":
                # Wrong token
                return Response(status=status.HTTP_400_BAD_REQUEST)
            user_id = loadedObject["user_id"]
            # Verify password is a string
            if not "password" in request.data:
                raise ValueError("Missing new password")
            if type(request.data["password"]) != str:
                raise ValueError("Password must be a string")
            validate_password(request.data["password"])

            # User is most likely not logged in when requesting a password change request, use user specified in token
            user = User.objects.get(id=user_id)
            # Change password in database
            user.set_password(request.data["password"])
            return Response(status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except signing.SignatureExpired as e:
            # Token expired
            return Response("Request expired!", status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ChangeMailView(generics.CreateAPIView):
    serializer_class = serializers.Serializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Create a request to change the users e-mail

        user = request.user
        # Verify users password again to make sure the request comes from the user and not someone hijacking the session
        if not user.check_password(request.data["password"]):
            return Response("Wrong password", status=status.HTTP_403_FORBIDDEN)

        try:
            # Check if the mail is already in use. If yes, fail silently to not leak information
            _ = User.objects.get(email=request.data["newEmail"])
        except User.DoesNotExist:
            # Mail not in use currently
            # Send the mail to the new mail address
            send_verification_mail(user, request.data["newEmail"], request)
        return Response(status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='ip', rate='1/s'), name="dispatch")
class ConfirmMailView(generics.RetrieveAPIView):
    serializer_class = serializers.Serializer

    # User doesnt need to be logged in, all required information and authorisation is provided by posessing the token

    def get(self, request, *args, **kwargs):
        try:
            # Load data from token and check expiration
            loadedObject = signing.loads(kwargs["token"], max_age=settings.TOKEN_MAX_LIFETIME)  # 15 minute timeout
            # Check if token type is an e-mail change token and not another signed by this server
            if "token_type" not in loadedObject or loadedObject["token_type"] != "EMAIL_CHANGE":
                # Wrong token
                return Response(status=status.HTTP_400_BAD_REQUEST)
            # User might not be logged in on the device the mail arrives, use user specified in token
            user = User.objects.get(id=loadedObject["user"])
            # Update databse entries
            user.email = loadedObject["email"]
            user.is_verified = True
            user.save()
            # TODO: Redirect to success/failure pages
            return Response("Email confirmed", status=status.HTTP_200_OK)
        except signing.SignatureExpired as e:
            # Token expired
            return Response("Request expired!", status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            # DB-Constrain violated
            return Response("E-Mail already in use", status=status.HTTP_400_BAD_REQUEST)


@method_decorator(ratelimit(key='user', rate='1/1s'), name="dispatch")
class PasswordChangeView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            # Verify users password again to make sure the request comes from the user and not someone hijacking the session
            if not user.check_password(request.data["oldPassword"]):
                return Response("Wrong password", status=status.HTTP_403_FORBIDDEN)
            validate_password(request.data["newPassword"])
            # Change password in database
            user.set_password(request.data["newPassword"])
            user.save()
            return Response(status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

