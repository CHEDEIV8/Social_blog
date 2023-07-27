from django.core.paginator import Paginator


def paginator(request, posts, SORT_VALUE):
    paginator = Paginator(posts, SORT_VALUE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
