from django.urls import path
from . import views

urlpatterns = [
    path('upload/',              views.UploadView.as_view(),      name='upload'),
    path('analyze/',             views.AnalyzeView.as_view(),     name='analyze'),
    path('decompose/',           views.DecomposeView.as_view(),   name='decompose'),
    path('equalize/',            views.EqualizeView.as_view(),    name='equalize'),
    path('modes/',               views.ModesListView.as_view(),   name='modes-list'),
    path('modes/<str:mode_name>/', views.ModeDetailView.as_view(), name='mode-detail'),
    path('wavelets/',            views.WaveletsView.as_view(),    name='wavelets'),
    path('audio/export/',        views.AudioExportView.as_view(), name='audio-export'),
]
