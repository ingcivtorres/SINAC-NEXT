"""Paginación opcional: solo se aplica cuando el cliente envía ?page=, así los paneles actuales siguen recibiendo listas."""
from rest_framework.pagination import PageNumberPagination


class PaginacionOpcional(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 200

    def paginate_queryset(self, queryset, request, view=None):
        if self.page_query_param not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


def paginar(request, elementos):
    """Devuelve (elementos de la página, metadatos) si se pidió ?page=; de lo contrario (elementos, None)."""
    paginador = PaginacionOpcional()
    pagina = paginador.paginate_queryset(elementos, request)
    if pagina is None:
        return elementos, None
    return pagina, {
        'pagina': paginador.page.number,
        'paginas': paginador.page.paginator.num_pages,
        'total': paginador.page.paginator.count,
        'tamano': paginador.get_page_size(request),
    }
