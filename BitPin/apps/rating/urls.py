from django.urls import path, include
from . import views
urlpatterns = [
    path('article/list/', views.ArticleListView.as_view(), name='artile_list'),
    path('article/<int:article_id>/rate/', views.RatingView.as_view(), name='artile_rate'),
]