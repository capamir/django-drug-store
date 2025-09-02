from django.views.generic import ListView
from products.models import Category
from mixins import AdminRequiredMixin 
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q

class AdminCategoryListView(AdminRequiredMixin, ListView):
    """
    Admin view for managing product categories with comprehensive functionality.
    Provides category statistics, search, and AJAX operations.
    """
    model = Category
    template_name = 'products/admin/CategoryList.html'
    context_object_name = 'categories'
    paginate_by = 20
    ordering = ['-id']  # Show newest first

    def get_queryset(self):
        """
        Optimized queryset with product counts and search functionality.
        """
        queryset = Category.objects.annotate(
            total_products=Count('products'),
            active_products=Count('products', filter=Q(products__is_active=True)),
            recommended_products=Count('products', filter=Q(products__recommended=True))
        ).select_related()
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Status filter
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        """
        Add comprehensive statistics and search context.
        """
        context = super().get_context_data(**kwargs)
        
        # Category statistics
        context.update({
            'total_categories': Category.objects.count(),
            'active_categories': Category.objects.filter(is_active=True).count(),
            'empty_categories': Category.objects.annotate(
                product_count=Count('products')
            ).filter(product_count=0).count(),
            
            # Search and filter context
            'current_search': self.request.GET.get('search', ''),
            'current_status': self.request.GET.get('status', ''),
            
            # Breadcrumb and page info
            'page_title': 'مدیریت دسته‌بندی‌ها',
            'show_add_button': True,
        })
        
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle AJAX operations for bulk actions.
        """
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
        
        action = request.POST.get('action')
        category_ids = request.POST.getlist('category_ids')
        
        if not action or not category_ids:
            return JsonResponse({'success': False, 'message': 'Missing parameters'}, status=400)
        
        try:
            categories = Category.objects.filter(id__in=category_ids)
            
            if action == 'activate':
                categories.update(is_active=True)
                message = f'{categories.count()} دسته‌بندی فعال شد'
                
            elif action == 'deactivate':
                categories.update(is_active=False)
                message = f'{categories.count()} دسته‌بندی غیرفعال شد'
                
            elif action == 'delete':
                # Check for categories with products
                categories_with_products = categories.annotate(
                    product_count=Count('products')
                ).filter(product_count__gt=0)
                
                if categories_with_products.exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'نمی‌توان دسته‌بندی‌هایی که دارای محصول هستند را حذف کرد'
                    }, status=400)
                
                count = categories.count()
                categories.delete()
                message = f'{count} دسته‌بندی حذف شد'
                
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
            
            return JsonResponse({'success': True, 'message': message})
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': 'خطا در انجام عملیات'
            }, status=500)


class AdminCategoryToggleView(AdminRequiredMixin, ListView):
    """
    AJAX view for quick category status toggle.
    """
    def post(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False}, status=400)
        
        category_id = kwargs.get('category_id')
        try:
            category = get_object_or_404(Category, id=category_id)
            category.is_active = not category.is_active
            category.save()
            
            return JsonResponse({
                'success': True,
                'is_active': category.is_active,
                'message': f'دسته‌بندی {category.name} {"فعال" if category.is_active else "غیرفعال"} شد'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'خطا در تغییر وضعیت'}, status=500)
