from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from .models import Product, Category
from .forms import ProductForm, CategoryForm
from .mixins import AdminRequiredMixin 


class HomeView(TemplateView):
    template_name = "products/Home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recommended_products'] = Product.objects.recommended()[:6]
        context['discounted_products'] = Product.objects.discounted()[:12]

        return context


class AdminProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = "products/admin/ProductList.html"
    context_object_name = "products"
    paginate_by = 20  # Show 20 products per page
    ordering = ['-id']  # Show newest products first

    def get_queryset(self):
        """Optimize queries with select_related for category"""
        return Product.objects.select_related('category').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add product statistics
        context['total_products'] = Product.objects.count()
        context['active_products'] = Product.objects.filter(is_active=True).count()
        context['recommended_products_count'] = Product.objects.filter(recommended=True).count()
        
        # Commented for future use
        # context['inactive_products'] = Product.objects.filter(is_active=False).count()
        # context['low_stock_products'] = Product.objects.filter(
        #     quantity__lte=models.F('reorder_level')
        # ).count()
        
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


class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:product_list')


class CategoryListView(ListView):
    model = Category
    template_name = 'products/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by('name')


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get active products in this category ordered by name
        context['products'] = Product.objects.filter(
            category=self.object,
            is_active=True
        ).order_by('name')
        return context


class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category_list')

class CategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'products/category_confirm_delete.html'
    success_url = reverse_lazy('products:category_list')
