from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Main certificate sending view
    path('', views.send_certificates_view, name='send_certificates'),
    
    # Progress tracking endpoint (AJAX)
    path('progress/<int:batch_id>/', views.get_batch_progress, name='batch_progress'),
    
    # Template management
    path('templates/', views.TemplateListView.as_view(), name='templates_list'),
    path('templates/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:pk>/preview/', views.preview_template, name='template_preview'),
]