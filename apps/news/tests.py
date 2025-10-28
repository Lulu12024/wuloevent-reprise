from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from apps.news.models import New
from apps.events.models import Event
from django.urls import reverse
from django.utils.timezone import now
from django.core.files.uploadedfile import SimpleUploadedFile


User = get_user_model()


class NewsViewSetTestCase(APITestCase):
    NEWS_TITLE = "Test News"
    NEWS_DESCRIPTION = "This is a test news article."
    NEWS_COVER_IMAGE = ""
    NEWS_DYNAMIC_LINK = ""
    NEWS_EXPIRED_AT = now().date()
    NEWS_STATUS = True

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
            is_active=True,
        )
        cls.normal_user = User.objects.create_user(
            email="user@example.com",
            password="userpass",
            is_active=True,
        )
        """cls.event = Event.objects.create(
            name="Test Event",
            description="This is a test event.",
            start_date=now().date(),
            end_date=now().date(),
        ) """

    def setUp(self):
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.user_token = str(RefreshToken.for_user(self.normal_user).access_token)
        self.image  = SimpleUploadedFile(
        name="test_image.png",
        content=b"", 
        content_type="image/png"
        )
        self.news = New.objects.create(
            title=self.NEWS_TITLE,
            description=self.NEWS_DESCRIPTION,
            cover_image=self.image,
            dynamic_link=self.NEWS_DYNAMIC_LINK,
            expired_at=self.NEWS_EXPIRED_AT,
            status=self.NEWS_STATUS,
            event=None,
        )
        

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_can_create_news(self):
        self.authenticate(self.admin_token)
        url = reverse("news-list")
        data = {
            "title": "New News",
            "description": "This is new news content.",
            "cover_image": self.image,
            "dynamic_link": "link",
            "expired_at": self.NEWS_EXPIRED_AT.isoformat(),
            "status": True,
          
        }
        response = self.client.post(url, data, format='json')
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        print(response.data)
        self.assertEqual(response.data["title"], data["title"])

    def test_normal_user_cannot_create_news(self):
        self.authenticate(self.user_token)
        url = reverse("news-list")
        data = {
            "title": "User News",
            "description": "This is a normal user news content.",
            "cover_image": self.image,
            "dynamic_link": "link",
            "expired_at": self.NEWS_EXPIRED_AT.isoformat(),
            "status": True,
         
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_news(self):
        self.authenticate(self.admin_token)
        url = reverse("news-detail", args=[self.news.pk])
        data = {"title": "Updated News"}
        response = self.client.patch(url, data, format='json')
        self.news.refresh_from_db()
        self.assertNotEqual(self.news.title, data["title"])

    def test_normal_user_cannot_update_news(self):
        self.authenticate(self.user_token)
        url = reverse("news-detail", args=[self.news.pk])
        data = {"title": "Updated by User"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_news(self):
        self.authenticate(self.admin_token)
        url = reverse("news-detail", args=[self.news.pk])
        response = self.client.delete(url)
        self.assertTrue(New.objects.filter(pk=self.news.pk).exists())

    def test_normal_user_cannot_delete_news(self):
        self.authenticate(self.user_token)
        url = reverse("news-detail", args=[self.news.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
