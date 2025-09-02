from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from .models import Product, Category
from .forms import ProductForm, CategoryForm
from mixins import AdminRequiredMixin 
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse

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


class AdminProductDetailView(AdminRequiredMixin, DetailView):
    model = Product
    template_name = 'products/admin/ProductDetail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'product_id'  # e.g. /admin/products/123/
    extra_context = {
        'page_title': 'جزئیات محصول'
    }

    def get_queryset(self):
        # Only active and inactive; may customize for soft-deletes etc
        return Product.objects.select_related('category').prefetch_related('related_products')

    def get_context_data(self, **kwargs):
        """Add extra context for the detail page."""
        context = super().get_context_data(**kwargs)
        product = context['product']
        context.update({
            "related_products": product.related_products.all(),
            "recommended": product.recommended,
            "category": product.category,
            "low_stock": product.low_stock,
            "effective_unit_price": product.effective_unit_price,
        })
        return context


class AdminProductCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Admin view for creating new products with proper permissions and messaging.
    """
    model = Product
    form_class = ProductForm
    template_name = 'products/admin/ProductForm.html'
    success_url = reverse_lazy('products:admin_product_list')
    success_message = "محصول «%(name)s» با موفقیت اضافه شد"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'افزودن محصول جدید'
        context['form_action'] = 'create'
        return context

    def form_valid(self, form):
        """Add custom logic before saving the product"""
        # Auto-generate slug if empty
        if not form.cleaned_data.get('slug'):
            from django.utils.text import slugify
            form.instance.slug = slugify(form.cleaned_data['name'])
        
        response = super().form_valid(form)
        
        # Log the creation (optional)
        messages.info(
            self.request, 
            f"محصول با کد {self.object.sku} در سیستم ثبت شد"
        )
        return response

    def form_invalid(self, form):
        """Handle form validation errors"""
        messages.error(
            self.request, 
            "لطفاً خطاهای فرم را بررسی و تصحیح کنید"
        )
        return super().form_invalid(form)


class AdminProductUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Admin view for updating existing products with proper permissions and messaging.
    """
    model = Product
    form_class = ProductForm
    template_name = 'products/admin/ProductForm.html'
    success_url = reverse_lazy('products:admin_product_list')
    success_message = "محصول «%(name)s» با موفقیت ویرایش شد"
    pk_url_kwarg = 'product_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'ویرایش محصول: {self.object.name}'
        context['form_action'] = 'update'
        return context

    def get_object(self, queryset=None):
        """Override to add custom object retrieval logic"""
        obj = super().get_object(queryset)
        # Add any additional checks here
        return obj

    def form_valid(self, form):
        """Add custom logic before saving updates"""
        response = super().form_valid(form)
        
        # Check for stock level warnings
        if self.object.low_stock:
            messages.warning(
                self.request,
                f"توجه: موجودی محصول {self.object.name} کم است ({self.object.quantity} واحد)"
            )
        
        return response

    def form_invalid(self, form):
        """Handle form validation errors"""
        messages.error(
            self.request, 
            "خطا در ویرایش محصول. لطفاً مجدداً تلاش کنید"
        )
        return super().form_invalid(form)


class AdminProductDeleteView(AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    """
    Admin view for deleting products with AJAX support.
    """
    model = Product
    success_url = reverse_lazy('products:admin_product_list')
    success_message = "محصول با موفقیت حذف شد"
    pk_url_kwarg = 'product_id'

    def delete(self, request, *args, **kwargs):
        """Handle both AJAX and regular delete requests"""
        self.object = self.get_object()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            try:
                product_name = self.object.name
                self.object.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'محصول "{product_name}" با موفقیت حذف شد'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'خطا در حذف محصول'
                }, status=400)
        else:
            # Regular request
            messages.success(request, self.success_message)
            return super().delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Prevent GET requests - only allow POST/DELETE"""
        messages.error(request, "متد درخواست نامعتبر است")
        return redirect(self.success_url)


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
