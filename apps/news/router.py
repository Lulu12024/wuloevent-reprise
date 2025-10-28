from rest_framework.routers import DefaultRouter
from apps.news.viewsests import NewViewSet

router = DefaultRouter()
router.register(r'news', NewViewSet, basename='news')
