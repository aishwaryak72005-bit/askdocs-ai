from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({
        "status": "online",
        "message": "DocuMind AI Backend API is running successfully.",
        "endpoints": {
            "admin": "/admin/",
            "api": "/api/"
        }
    })

urlpatterns = [
    path("", root_view, name="api_root"),
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("chat.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
