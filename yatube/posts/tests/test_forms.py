import tempfile
import shutil

from http import HTTPStatus
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Leo')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test_slug',
                                         description='Тестовое описание')

        cls.post = Post.objects.create(text='Тестовый пост',
                                       group=cls.group,
                                       author=cls.user)
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='image.png',
            content=cls.image,
            content_type='image/png'
        )
        cls.posts_count = Post.objects.count()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        '''Проверка создания поста с картинкой'''

        form_data = {
            'text': 'Пост с картинкой',
            'group': f'{self.group.id}',
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), (self.posts_count + 1))
        self.assertTrue(Post.objects.filter(
                        text=form_data['text'],
                        group=form_data['group'],
                        author=self.user,
                        image='posts/image.png',
                        ).exists())

        self.assertRedirects(response, reverse('posts:profile',
                             args=(self.user.username,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post(self):
        '''Проверка изменения поста'''

        form_data = {
            'text': 'Тестовый текст',
            'group': f'{self.group.id}',
        }
        edit_post = Post.objects.get(text='Тестовый пост')

        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(edit_post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), self.posts_count)
        self.assertTrue(Post.objects.filter(
                        text=form_data['text'],
                        group=form_data['group'],
                        author=self.user,
                        ).exists())

        self.assertRedirects(response, reverse('posts:post_detail',
                             args=(edit_post.id,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_comments_authorized_user(self):
        '''Проверка создания коментария авторизированным пользователем'''

        add_comment_url = reverse('posts:add_comment', args=(self.post.pk,))
        form_data = {'text': 'Коментарий'}
        response = self.authorized_client.post(add_comment_url,
                                               data=form_data,
                                               follow=True
                                               )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     args=(self.post.id,)))
        self.assertEqual(Comment.objects.count(), 1)
        self.assertTrue(Comment.objects.filter(
                        text=form_data['text'],
                        author=self.user,
                        post=self.post
                        ).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_comments_guest_user(self):
        '''Проверка создания коментария неавторизированным пользователем'''

        add_comment_url = reverse('posts:add_comment', args=(self.post.pk,))
        response = self.guest_client.post(add_comment_url,
                                          data={'text': 'Коментарий'},
                                          follow=True
                                          )
        self.assertRedirects(response,
                             reverse('users:login')
                             + '?next=' + add_comment_url)
