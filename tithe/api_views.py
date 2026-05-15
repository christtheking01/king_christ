from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from .models import TithePayment, TitheReceipt
from member.models import Member
from .serializers import (
    MemberListSerializer,
    TithePaymentSerializer,
    TithePaymentCreateSerializer,
    TitheReceiptSerializer,
    POSTitheSubmissionSerializer
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_member_lookup(request):
    #search for members by name, code, or telephone
    search_term = request.query_params.get('search','').strip()
    if len(search_term) < 3:
        return Response(
            {'error':'Search term must be at least 3 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        members = Member.objects.filter(
            Q(name__icontains=search_term) |
            Q(code__icontains=search_term) |
            Q(telephone__icontains=search_term)
        ).filter(active=True).order_by('name')[:10] 
        serializer = MemberListSerializer(members, many=True)

        return Response({
            'success': True,
            'count': members.count(),
            'results': serializer.data,
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_payment(request):
    """
    Submit a new tithe payment from POS.
    Creates payment and auto-generates receipt.
    
    POST /tithe/api/v1/payments/submit/
    Body: {
        "member_id": 123,
        "amount": 50000.00,
        "payment_method": "cash",
        "auto_print": true
    }
    """
    # Validate input data
    serializer = POSTitheSubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    
    try:
        # Get the member
        member = Member.objects.get(id=data['member_id'])
        
        # Create the tithe payment
        payment = TithePayment.objects.create(
            name=member,
            amount=data['amount'],
            status=data['payment_method'],
            contact_number=str(member.telephone) if member.telephone else '',
            date=timezone.now()
        )
        
        # Auto-generate receipt if enabled
        receipt = None
        if getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True):
            user = request.user
            generated_by = user.get_full_name() if user else 'POS System'
            
            receipt = TitheReceipt.objects.create(
                tithe_payment=payment,
                generated_by=generated_by,
                church_name=settings.CHURCH_NAME,
                church_address=settings.CHURCH_ADDRESS,
                church_phone=settings.CHURCH_PHONE,
            )
            
            # Auto-mark as printed if requested
            if data.get('auto_print') and getattr(settings, 'TITHE_AUTO_PRINT_RECEIPT', False):
                receipt.mark_printed()
        
        # Serialize and return the payment
        payment_serializer = TithePaymentSerializer(payment)
        
        return Response({
            'success': True,
            'message': 'Payment submitted successfully',
            'payment': payment_serializer.data,
            'receipt': TitheReceiptSerializer(receipt).data if receipt else None
        }, status=status.HTTP_201_CREATED)
        
    except Member.DoesNotExist:
        return Response(
            {'error': 'Member not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_recent_payments(request):
    """
    Get the last 10 tithe payments.
    Used by POS dashboard to show recent activity.
    
    GET /tithe/api/v1/payments/recent/
    """
    try:
        # Get last 10 payments with member data
        payments = TithePayment.objects.select_related(
            'name'
        ).order_by('-date')[:10]
        
        serializer = TithePaymentSerializer(payments, many=True)
        
        return Response({
            'success': True,
            'count': payments.count(),
            'results': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_print_receipt(request, receipt_id):
    """
    Mark a receipt as printed.
    Called by POS after printing receipt.
    
    POST /tithe/api/v1/receipts/<id>/print/
    """
    try:
        receipt = TitheReceipt.objects.get(id=receipt_id)
        receipt.mark_printed()
        
        return Response({
            'success': True,
            'message': 'Receipt marked as printed',
            'receipt_number': receipt.receipt_number
        })
        
    except TitheReceipt.DoesNotExist:
        return Response(
            {'error': 'Receipt not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_payment_detail(request, payment_id):
    """
    Get full details of a specific payment including receipt.
    
    GET /tithe/api/v1/payments/<id>/
    """
    try:
        payment = TithePayment.objects.select_related('name').get(id=payment_id)
        
        # Get receipt if exists
        receipt = getattr(payment, 'receipt', None)
        
        return Response({
            'success': True,
            'payment': TithePaymentSerializer(payment).data,
            'receipt': TitheReceiptSerializer(receipt).data if receipt else None
        })
        
    except TithePayment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard_stats(request):
    """
    Get dashboard statistics for POS mobile app.
    Returns today's summary, recent activity, and quick stats.
    
    GET /tithe/api/v1/dashboard/stats/
    """
    try:
        from django.db.models import Sum, Count, Q
        from django.utils import timezone
        from datetime import datetime
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        # Today's statistics
        today_payments = TithePayment.objects.filter(date__gte=today_start)
        today_total = today_payments.aggregate(total=Sum('amount'))['total'] or 0
        today_count = today_payments.count()
        
        # Cash vs Bank breakdown
        cash_total = today_payments.filter(status='cash').aggregate(total=Sum('amount'))['total'] or 0
        bank_total = today_payments.filter(status='bank').aggregate(total=Sum('amount'))['total'] or 0
        
        # Recent payments (last 10)
        recent_payments = TithePayment.objects.select_related('name').order_by('-date')[:10]
        
        # Top contributors today
        top_contributors = today_payments.values(
            'name__id', 'name__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:5]
        
        # This week's stats
        week_start = today - timezone.timedelta(days=today.weekday())
        week_payments = TithePayment.objects.filter(date__date__gte=week_start)
        week_total = week_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Member statistics
        total_members = Member.objects.filter(active=True).count()
        todays_payers = today_payments.values('name').distinct().count()
        
        return Response({
            'success': True,
            'data': {
                'today': {
                    'total_amount': float(today_total),
                    'payment_count': today_count,
                    'cash_amount': float(cash_total),
                    'bank_amount': float(bank_total),
                    'unique_payers': todays_payers,
                },
                'week': {
                    'total_amount': float(week_total),
                    'payment_count': week_payments.count(),
                },
                'stats': {
                    'total_members': total_members,
                    'average_payment': float(today_total / today_count) if today_count > 0 else 0,
                },
                'recent_payments': TithePaymentSerializer(recent_payments, many=True).data,
                'top_contributors': list(top_contributors),
            }
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_sync_members(request):
    """
    Bulk sync members data for mobile app offline support.
    Supports pagination and incremental sync based on last_modified.
    
    GET /tithe/api/v1/sync/members/
    Query params:
    - page: Page number (default: 1)
    - limit: Items per page (default: 100, max: 500)
    - since: ISO datetime for incremental sync (optional)
    - community: Filter by community ID (optional)
    """
    try:
        from django.core.paginator import Paginator
        from django.utils import timezone
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 100)), 500)  # Max 500 items
        since_str = request.GET.get('since')
        community_id = request.GET.get('community')
        
        # Build queryset
        members = Member.objects.filter(active=True).select_related('shepherd', 'ministry')
        
        # Apply filters
        if since_str:
            try:
                since_date = timezone.datetime.fromisoformat(since_str.replace('Z', '+00:00'))
                members = members.filter(
                    Q(updated_at__gte=since_date) | Q(created_at__gte=since_date)
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid since parameter format. Use ISO datetime.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if community_id:
            members = members.filter(shepherd_id=community_id)
        
        # Order by updated_at for consistent pagination
        members = members.order_by('updated_at', 'id')
        
        # Paginate
        paginator = Paginator(members, limit)
        members_page = paginator.get_page(page)
        
        # Serialize data
        serializer = MemberListSerializer(members_page, many=True)
        
        # Get sync metadata
        latest_member = members.order_by('-updated_at').first()
        latest_timestamp = latest_member.updated_at if latest_member else None
        
        return Response({
            'success': True,
            'data': {
                'members': serializer.data,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': members_page.has_next(),
                    'has_previous': members_page.has_previous(),
                },
                'sync_info': {
                    'latest_timestamp': latest_timestamp.isoformat() if latest_timestamp else None,
                    'items_in_sync': paginator.count,
                    'filters_applied': {
                        'since': since_str,
                        'community': community_id,
                    }
                }
            }
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_pos_settings(request):
    """
    Get POS configuration settings for mobile app.
    Includes church info, receipt settings, and app configuration.
    
    GET /tithe/api/v1/settings/pos/
    """
    try:
        from django.conf import settings
        
        # Get church settings from Django settings or defaults
        church_settings = {
            'name': getattr(settings, 'CHURCH_NAME', 'Christ The King Parish'),
            'address': getattr(settings, 'CHURCH_ADDRESS', ''),
            'phone': getattr(settings, 'CHURCH_PHONE', ''),
            'email': getattr(settings, 'CHURCH_EMAIL', ''),
        }
        
        # POS configuration
        pos_settings = {
            'auto_generate_receipt': getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True),
            'auto_print_receipt': getattr(settings, 'TITHE_AUTO_PRINT_RECEIPT', False),
            'default_payment_method': 'cash',
            'receipt_width': getattr(settings, 'RECEIPT_WIDTH', 32),
            'currency_symbol': 'Tsh',
            'decimal_places': 2,
        }
        
        # App configuration
        app_settings = {
            'app_version': '1.0.0',
            'api_version': 'v1',
            'supported_languages': ['en', 'sw'],
            'default_language': 'en',
            'search_min_length': 3,
            'max_payment_amount': 1000000.0,
            'min_payment_amount': 100.0,
        }
        
        # User permissions
        user = request.user
        user_permissions = {
            'can_submit_payments': True,  # All authenticated users can submit
            'can_print_receipts': True,
            'can_view_reports': user.is_staff or user.roles in ['admin', 'treasurer', 'accountant'],
            'can_manage_members': user.is_staff or user.roles in ['admin', 'priest', 'catechist'],
        }
        
        return Response({
            'success': True,
            'data': {
                'church': church_settings,
                'pos': pos_settings,
                'app': app_settings,
                'user': {
                    'username': user.username,
                    'role': user.roles,
                    'permissions': user_permissions,
                },
                'features': {
                    'offline_mode': True,
                    'qr_scanning': True,
                    'bluetooth_printing': True,
                    'push_notifications': True,  # Now implemented
                }
            }
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_register_device(request):
    """
    Register a mobile device for push notifications and tracking.
    
    POST /tithe/api/v1/device/register/
    Body: {
        "device_id": "unique_device_id",
        "device_type": "android|ios",
        "push_token": "firebase_token",
        "device_name": "Samsung Galaxy S21",
        "app_version": "1.0.0"
    }
    """
    try:
        from .models import DeviceRegistration
        
        data = request.data
        required_fields = ['device_id', 'device_type']
        
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {'error': f'{field} is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate device type
        if data['device_type'] not in ['android', 'ios']:
            return Response(
                {'error': 'Invalid device type. Must be android or ios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Register device
        device, created = DeviceRegistration.register_device(
            user=request.user,
            device_id=data['device_id'],
            device_type=data['device_type'],
            push_token=data.get('push_token'),
            device_name=data.get('device_name'),
            app_version=data.get('app_version'),
        )
        
        return Response({
            'success': True,
            'message': 'Device registered successfully' if created else 'Device updated successfully',
            'device_id': device.device_id,
            'is_new': created,
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_sync_offline_operations(request):
    """
    Sync offline operations from mobile app.
    
    POST /tithe/api/v1/sync/offline/
    Body: {
        "operations": [
            {
                "operation_type": "create_payment",
                "data": {...},
                "client_timestamp": "2024-01-01T12:00:00Z"
            }
        ]
    }
    """
    try:
        from .models import DeviceRegistration, OfflineOperation, SyncLog
        from django.utils import timezone
        
        data = request.data
        operations = data.get('operations', [])
        
        if not operations:
            return Response(
                {'error': 'No operations provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get device info
        device_id = data.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = DeviceRegistration.objects.get(device_id=device_id, user=request.user)
        except DeviceRegistration.DoesNotExist:
            return Response(
                {'error': 'Device not registered'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create sync log
        sync_log = SyncLog.objects.create(
            device=device,
            sync_type='payments',  # Could be extended based on operation types
            total_items=len(operations),
        )
        
        results = []
        synced_count = 0
        
        for op_data in operations:
            operation_type = op_data.get('operation_type')
            operation_data = op_data.get('data')
            
            try:
                # Process operation based on type
                if operation_type == 'create_payment':
                    # Create payment from offline data
                    member_id = operation_data.get('member_id')
                    amount = operation_data.get('amount')
                    payment_method = operation_data.get('payment_method', 'cash')
                    
                    if not member_id or not amount:
                        raise ValueError('Missing required payment fields')
                    
                    member = Member.objects.get(id=member_id)
                    payment = TithePayment.objects.create(
                        name=member,
                        amount=amount,
                        status=payment_method,
                        contact_number=str(member.telephone) if member.telephone else '',
                        date=timezone.now(),  # Use server time for consistency
                    )
                    
                    # Generate receipt if enabled
                    from django.conf import settings
                    if getattr(settings, 'TITHE_AUTO_GENERATE_RECEIPT', True):
                        TitheReceipt.objects.create(
                            tithe_payment=payment,
                            generated_by=f"{request.user.username} (Mobile)",
                            church_name=getattr(settings, 'CHURCH_NAME', 'Christ The King Parish'),
                        )
                    
                    results.append({
                        'success': True,
                        'operation_type': operation_type,
                        'payment_id': payment.id,
                    })
                    synced_count += 1
                    
                else:
                    raise ValueError(f'Unsupported operation type: {operation_type}')
                
            except Exception as e:
                # Store failed operation for retry
                OfflineOperation.objects.create(
                    device=device,
                    operation_type=operation_type,
                    data=op_data,
                    status='failed',
                    error_message=str(e),
                )
                
                results.append({
                    'success': False,
                    'operation_type': operation_type,
                    'error': str(e),
                })
        
        # Update sync log
        sync_log.mark_completed(items_synced=synced_count)
        
        return Response({
            'success': True,
            'message': f'Sync completed: {synced_count}/{len(operations)} operations processed',
            'sync_id': sync_log.id,
            'results': results,
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )