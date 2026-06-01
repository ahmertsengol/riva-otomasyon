"""Giriş/çıkış ve OTP tabanlı şifre sıfırlama akışı."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from apps.accounts.forms import (
    ChangePasswordForm,
    LoginForm,
    NewPasswordForm,
    OTPVerifyForm,
    PasswordResetRequestForm,
)
from apps.accounts.models import OTPCode, User
from apps.core.otp import get_channel

# Şifre sıfırlama akışında adımlar arası taşınan oturum anahtarları
SESSION_USER = "pwreset_user_id"
SESSION_OTP = "pwreset_otp_id"
SESSION_VERIFIED = "pwreset_verified"


class RivaLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    messages.info(request, "Çıkış yapıldı.")
    return redirect("accounts:login")


class RivaPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = ChangePasswordForm
    success_url = reverse_lazy("settings:index")

    def form_valid(self, form):
        messages.success(self.request, "Şifreniz güncellendi.")
        return super().form_valid(form)


def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.find_user()
            channel = get_channel(form.cleaned_data["channel"])
            # Kullanıcı var ve kanal kullanılabilirse kod gönder.
            if user and channel.can_use(user):
                otp, code = OTPCode.issue(user, channel=channel.key)
                channel.send(user, code)
                request.session[SESSION_USER] = user.pk
                request.session[SESSION_OTP] = otp.pk
                request.session.pop(SESSION_VERIFIED, None)
                messages.success(
                    request,
                    f"Doğrulama kodu gönderildi ({channel.target_hint(user)}).",
                )
                return redirect("accounts:password_reset_verify")
            messages.error(
                request,
                "Bu bilgilerle kod gönderilemedi. Kullanıcı adını/e-postayı kontrol edin.",
            )
    else:
        form = PasswordResetRequestForm()
    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_verify(request):
    otp_id = request.session.get(SESSION_OTP)
    if not otp_id:
        return redirect("accounts:password_reset")
    otp = OTPCode.objects.filter(pk=otp_id).first()
    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            if otp and otp.verify(form.cleaned_data["code"]):
                request.session[SESSION_VERIFIED] = True
                return redirect("accounts:password_reset_set")
            messages.error(request, "Kod hatalı veya süresi dolmuş.")
    else:
        form = OTPVerifyForm()
    return render(request, "accounts/password_reset_verify.html", {"form": form})


def password_reset_set(request):
    if not request.session.get(SESSION_VERIFIED):
        return redirect("accounts:password_reset")
    user = User.objects.filter(pk=request.session.get(SESSION_USER)).first()
    if not user:
        return redirect("accounts:password_reset")
    if request.method == "POST":
        form = NewPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            for key in (SESSION_USER, SESSION_OTP, SESSION_VERIFIED):
                request.session.pop(key, None)
            messages.success(request, "Şifreniz güncellendi. Giriş yapabilirsiniz.")
            return redirect("accounts:login")
    else:
        form = NewPasswordForm(user)
    return render(request, "accounts/password_reset_set.html", {"form": form})
