# In your catechesis/views.py or context_processors.py

from django.db.models import Count, Q

def get_catechesis_context(request):
    """
    Context processor to add catechesis-related variables
    """
    context = {
        'catechesis_register_active': False,
        'catechesis_member_list': False,
        'catechesis_member_detail': False,
        'catechesis_sacrament_request_create': False,
        'catechesis_pending_request': False,
        'catechesis_review_request': False,
        'catechesis_sacrament_list': False,
        'catechesis_complete_request': False,
        'pending_requests_count': 0,
    }
    
    # Get current path
    path = request.path
    
    # Set active flags based on URL
    if path == '/catechesis/register/':
        context['catechesis_register_active'] = True
    elif path == '/catechesis/' or path.startswith('/catechesis/member/') and '/request-sacrament/' not in path:
        if 'member' in path and path.count('/') > 2:
            context['catechesis_member_detail'] = True
        else:
            context['catechesis_member_list'] = True
    elif '/request-sacrament/' in path:
        context['catechesis_sacrament_request_create'] = True
    elif path == '/catechesis/pending-requests/':
        context['catechesis_pending_request'] = True
    elif '/review/' in path:
        context['catechesis_review_request'] = True
    elif path == '/catechesis/sacraments/':
        context['catechesis_sacrament_list'] = True
    elif '/complete/' in path:
        context['catechesis_complete_request'] = True
    
    # Get pending requests count for approvers
    if request.user.is_authenticated and hasattr(request.user, 'is_approver') and request.user.is_approver():
        from .models import SacramentRequest
        
        pending_count = SacramentRequest.objects.filter(
            status='pending'
        ).count()
        
        # If catechist, exclude Marriage and Holy Orders
        if request.user.role == 'catechist':
            pending_count = SacramentRequest.objects.filter(
                status='pending'
            ).exclude(
                sacrament__name__in=['marriage', 'holy_orders']
            ).count()
        
        context['pending_requests_count'] = pending_count
    
    return context