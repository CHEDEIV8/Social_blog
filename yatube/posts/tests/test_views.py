import tempfile
import shutil

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Post, Group, Comment, Follow
from .. views import SORT_VALUE


User = get_user_model()
COUNT_POST = 13
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Koby')
        cls.authorized_client = Client()
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
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_two = Group.objects.create(
            title='Группа2',
            slug='group_two',
            description='Группа для других постов'
        )
        Post.objects.bulk_create(
            [Post(author=cls.user,
                  text='Тестовый пост',
                  group=cls.group,
                  image=cls.uploaded) for _ in range(COUNT_POST)])
        cls.posts = Post.objects.all()
        cls.comment = Comment.objects.create(post=cls.posts[0],
                                             author=cls.user,
                                             text='comment')
        cls.urls = [reverse('posts:index'),
                    reverse(
                    'posts:group_list', kwargs={'slug':
                                                f'{cls.group.slug}'}),
                    reverse(
                    'posts:profile', kwargs={'username':
                                             f'{cls.user.username}'})]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''

        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=(self.group.slug,)): 'posts/group_list.html',
            reverse('posts:profile',
                    args=(self.user.username,)): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=(self.posts.first().id,)): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args=(self.posts.first().id,)): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def page_obj_check(self, post):
        self.assertEqual(post.author, self.posts.first().author)
        self.assertEqual(post.text, self.posts.first().text)
        self.assertEqual(post.group, self.posts.first().group)
        self.assertEqual(post.image, self.posts.first().image)

    def test_index_show_correct_context(self):
        '''Шаблоны index сформированы
        с правильным контекстом.'''

        response = self.authorized_client.get(self.urls[0])
        post = response.context['page_obj'][0]
        self.page_obj_check(post)

    def test_group_list_show_correct_context(self):
        '''Шаблоны group_list сформированы
        с правильным контекстом.'''

        response = self.authorized_client.get(self.urls[1])
        post = response.context['page_obj'][0]
        self.page_obj_check(post)
        group = response.context['group']
        self.assertEqual(group, self.group)

    def test_profile_show_correct_context(self):
        '''Шаблоны profile сформированы
        с правильным контекстом.'''

        response = self.authorized_client.get(self.urls[2])
        post = response.context['page_obj'][0]
        self.page_obj_check(post)
        author = response.context['author']
        self.assertEqual(author, self.user)

    def test_post_editing_shows_correct_context(self):
        '''Шаблон post_edit сформирован с правильным контекстом.'''

        response = self.authorized_client.get(reverse(
            'posts:post_edit', args=(self.posts.first().id,)
        ))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context['is_edit'], True)

    def test_post_create_show_correct_context(self):
        '''Шаблон post_create сформирован с правильным контекстом.'''

        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_show_correct_context(self):
        '''Шаблон post_detail сформирован с правильным контекстом.'''

        response = (self.authorized_client.get(
            reverse('posts:post_detail', args=(self.posts.first().id,))
        ))
        post = response.context['post']
        self.page_obj_check(post)
        self.assertEqual(response.context.get('comments')[0].text,
                         self.comment.text)
        form_field = response.context.get('form').fields.get('text')
        self.assertIsInstance(form_field, forms.fields.CharField)

    def test_cache_index(self):
        '''Проверка хранения и очищения кэша для index.'''

        response = self.authorized_client.get(self.urls[0])
        content = response.content
        self.posts.delete()
        response_old = self.authorized_client.get(self.urls[0])
        old_conten = response_old.content
        self.assertEqual(old_conten, content)
        cache.clear()
        response_new = self.authorized_client.get(self.urls[0])
        new_conten = response_new.content
        self.assertNotEqual(new_conten, content)

    def test_no_post_in_wrong_group(self):
        '''Посты не попадают в другую группу'''

        for url in self.urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                post = response.context['page_obj'][0]
                self.assertNotEqual(post.group, self.group_two)

    def test_paginator_index_group_and_post_profile(self):
        '''Паджинатор отображает верное кол-во'''

        for url in self.urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                posts = response.context['page_obj']
                self.assertEqual(len(posts), SORT_VALUE)

                response = self.authorized_client.get(url + '?page=2')
                posts = response.context['page_obj']
                self.assertEqual(len(posts), (SORT_VALUE - 7))


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create_user(
            username='Автор',
        )
        cls.post_follower = User.objects.create_user(
            username='Подписчик',
        )
        cls.post = Post.objects.create(
            text='Подпишись на меня',
            author=cls.post_autor,
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.post_autor)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_follower)

    def test_follow_on_user(self):
        '''Проверка подписки на пользователя.'''
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                args=(self.post_autor,)))
        follow = Follow.objects.all()
        self.assertTrue(Follow.objects.filter(user=self.post_follower,
                                              author=self.post_autor).exists())
        self.assertEqual(count_follow + 1, follow.count())

    def test_unfollow_on_user(self):
        '''Проверка отписки от пользователя.'''
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                args=(self.post_autor,)))
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_follow_on_authors(self):
        '''Проверка записей у тех кто подписан.'''
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.follower_client.get(
            reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        '''Проверка записей у тех кто не подписан.'''
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'].object_list)
