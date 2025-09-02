from django.views.generic import ListView, DetailView, TemplateView
from products.models import Product

class HomeView(TemplateView):
    template_name = "products/Home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recommended_products'] = Product.objects.recommended()[:6]
        context['discounted_products'] = Product.objects.discounted()[:12]

        return context

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'  # Customize this path
    context_object_name = 'products'
    paginate_by = 20  # Pagination for scalability
    
    def get_queryset(self):
        # You can customize ordering or filtering here
        return Product.objects.filter(is_active=True).order_by('name')

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'  # Customize path
    context_object_name = 'product'
