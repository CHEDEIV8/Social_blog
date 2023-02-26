from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .utils import paginator


SORT_VALUE = 10


def index(request):
    posts = Post.objects.select_related('author', 'group').all()
    context = {
        'page_obj': paginator(request, posts, SORT_VALUE),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.post_set.select_related('author').all()
    context = {
        'group': group,
        'page_obj': paginator(request, posts, SORT_VALUE),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)

    following = (request.user.is_authenticated
                 and request.user.follower.filter(author=author).exists())
    posts = author.posts.select_related('group').all()
    context = {
        'author': author,
        'following': following,
        'page_obj': paginator(request, posts, SORT_VALUE),
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    form = CommentForm()
    context = {
        'post': post,
        'comments': comments,
        'form': form
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST,
                        files=request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            form.save()
            return redirect('posts:profile', username=post.author)
    else:
        form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(request.POST,
                    files=request.FILES,
                    instance=post)
    if request.method == 'POST':
        if form.is_valid():
            post.save()
            return redirect('posts:post_detail', post_id=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request,
                  'posts/create_post.html', {'form': form, 'is_edit': True})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post.id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    context = {'page_obj': paginator(request, posts, SORT_VALUE)}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if (author == request.user
       or request.user.follower.filter(author=author).exists()):
        return redirect('posts:profile', username=username)
    Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):

    author = get_object_or_404(User, username=username)
    request.user.follower.filter(author=author).delete()
    return redirect('posts:profile', username=username)
