# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.contrib.auth import get_user_model

User = get_user_model()


def make_user(email="user@test.com", password="pass123", **extra_fields):
    return User.objects.create_user(email=email, password=password, **extra_fields)
