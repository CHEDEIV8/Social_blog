from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus
from django.urls import reverse

from ..models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание',
        )
        cls.privat_url = {
            reverse('posts:post_edit', args=(cls.post.id,)):
            f'/auth/login/?next=/posts/{cls.post.id}/edit/',
            reverse('posts:post_create'):
            '/auth/login/?next=/create/',
            reverse('posts:add_comment', args=(cls.post.id,)):
            f'/auth/login/?next=/posts/{cls.post.id}/comment/',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_guest_client(self):
        '''Тест доступа неавторизированного пользователя
        к доступным страницам
        '''

        pages = ('/',
                 f'/group/{self.group.slug}/',
                 f'/profile/{self.user.username}/',
                 f'/posts/{self.post.id}/'
                 )
        for page in pages:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_privat_urls_to_authorized_and_guest_clien(self):
        '''Страницы /posts/post_id/edit/, /posts/post_id/comment/, /create/
        допускает зарегестрированных авторов постов и
        перенаправляет анонимных пользователей.
        '''

        for url, url_response in self.privat_url.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                if url == reverse('posts:add_comment', args=(self.post.id,)):
                    self.assertRedirects(response,
                                         reverse('posts:post_detail',
                                                 args=(self.post.id,)))
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

                response = self.guest_client.get(url)
                self.assertRedirects(response, url_response)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_urls_uses_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''

        templates_url_names = {
            '/': 'posts/index.html',
            '/follow/': 'posts/follow.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_for_non_existing_url(self):
        '''URL-адрес которого не существует.'''

        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
