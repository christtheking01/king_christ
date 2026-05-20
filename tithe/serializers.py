from rest_framework import serializers
from .models import TithePayment, TitheReceipt
from member.models import Member


class MemberSerializer(serializers.ModelSerializer):
    """Full member serializer — used internally."""
    class Meta:
        model = Member
        fields = [
            'id', 'name', 'code', 'telephone',
            'location', 'active', 'shepherd',
            'ministry', 'gender', 'membership_category',
        ]
        read_only_fields = ['id']


class MemberListSerializer(serializers.ModelSerializer):
    """Compact member serializer returned by the member-lookup endpoint."""
    community_name = serializers.CharField(source='shepherd.name', read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'name', 'code', 'telephone', 'location', 'community_name']


class TithePaymentSerializer(serializers.ModelSerializer):
    """
    Payment list/detail serializer consumed by the Flutter POS app.

    Key: the FK field on TithePayment is called `name` (historical naming).
    We expose it as both `name` (raw FK id, kept for compatibility) AND
    as an explicit `member_id` so the Flutter model can read it unambiguously.
    """
    member_id             = serializers.IntegerField(source='name.id',           read_only=True)
    member_name           = serializers.CharField(source='name.name',            read_only=True)
    member_code           = serializers.CharField(source='name.code',            read_only=True)
    member_telephone      = serializers.CharField(source='name.telephone',       read_only=True)
    payment_method_display = serializers.CharField(source='get_status_display',  read_only=True)

    class Meta:
        model = TithePayment
        fields = [
            'id',
            'date',
            'name',                  # raw FK id (kept for backwards compat)
            'member_id',             # explicit member id  ← NEW
            'member_name',
            'member_code',
            'member_telephone',      # ← NEW — useful for receipts
            'contact_number',
            'amount',
            'status',
            'payment_method_display',
            'sms_sent',
            'sms_sent_at',
        ]
        read_only_fields = ['id', 'date', 'sms_sent', 'sms_sent_at']


class TithePaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Tithe payment via POS."""
    class Meta:
        model = TithePayment
        fields = ['name', 'amount', 'status', 'contact_number']

    def validate(self, data):
        member = data.get('name')
        amount = data.get('amount')

        if not member:
            raise serializers.ValidationError({'name': 'Member is required'})
        if not amount or amount <= 0:
            raise serializers.ValidationError({'amount': 'Amount must be greater than zero'})
        if not data.get('contact_number') and member.telephone:
            data['contact_number'] = str(member.telephone)

        return data


class TitheReceiptSerializer(serializers.ModelSerializer):
    payment_amount = serializers.DecimalField(
        source='tithe_payment.amount', read_only=True, max_digits=10, decimal_places=2
    )
    payment_date  = serializers.DateTimeField(source='tithe_payment.date', read_only=True)
    member_name   = serializers.CharField(source='tithe_payment.name.name', read_only=True)

    class Meta:
        model = TitheReceipt
        fields = [
            'id', 'receipt_number', 'generated_at', 'generated_by',
            'is_printed', 'printed_at', 'print_attempts',
            'church_name', 'church_address', 'church_phone',
            'payment_amount', 'payment_date', 'member_name',
        ]
        read_only_fields = [
            'id', 'receipt_number', 'generated_at',
            'is_printed', 'printed_at', 'print_attempts',
        ]


class POSTitheSubmissionSerializer(serializers.Serializer):
    """Serializer for the POS tithe submission endpoint."""
    member_id      = serializers.IntegerField()
    amount         = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=[('cash', 'Cash'), ('bank', 'Bank')],
        default='cash',
    )
    auto_print = serializers.BooleanField(default=True)

    def validate_member_id(self, value):
        if not Member.objects.filter(id=value).exists():
            raise serializers.ValidationError('Member with this ID does not exist')
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero')
        return value
