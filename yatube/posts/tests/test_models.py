from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, LEN_STR_POST

User = get_user_model()


class PostAndGroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        '''Модель имеет корректный __str__'''

        group = PostAndGroupModelTest.group
        expected_object_name = group.title
        self.assertEqual(expected_object_name, str(group))

        post = PostAndGroupModelTest.post
        expected_object_name = post.text[:LEN_STR_POST]
        self.assertEqual(expected_object_name, str(post))
