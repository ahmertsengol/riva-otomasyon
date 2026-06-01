"""Giriş ve OTP tabanlı şifre sıfırlama formları."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm

User = get_user_model()

_INPUT = {"class": "input"}


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "input", "autofocus": True, "placeholder": "Kullanıcı adı"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "input", "placeholder": "Şifre"}
        )
        self.fields["username"].label = "Kullanıcı adı"
        self.fields["password"].label = "Şifre"


class PasswordResetRequestForm(forms.Form):
    identifier = forms.CharField(
        label="Kullanıcı adı veya e-posta",
        widget=forms.TextInput(attrs={**_INPUT, "autofocus": True}),
    )
    channel = forms.ChoiceField(
        label="Kodu nereye gönderelim?",
        choices=[("email", "E-posta"), ("whatsapp", "WhatsApp (yakında)")],
        initial="email",
        widget=forms.RadioSelect,
    )

    def find_user(self):
        ident = self.cleaned_data["identifier"].strip()
        return (
            User.objects.filter(username__iexact=ident).first()
            or User.objects.filter(email__iexact=ident).first()
        )


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        label="Doğrulama kodu",
        max_length=6,
        widget=forms.TextInput(
            attrs={
                **_INPUT,
                "autofocus": True,
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "6 haneli kod",
            }
        ),
    )


class NewPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("new_password1", "new_password2"):
            self.fields[name].widget.attrs.update({"class": "input"})


class ChangePasswordForm(PasswordChangeForm):
    """Giriş yapmış kullanıcının kendi şifresini değiştirmesi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("old_password", "new_password1", "new_password2"):
            self.fields[name].widget.attrs.update({"class": "input"})
