from django.shortcuts import render
from catechesis.models import SacramentRequest
from member.models import Member, Community,Committee,Ministry

# Create your views here.
def home(request):
    #'upcoming_events': Event.objects.filter(date__gte=timezone.now()).order_by('date')[:3],
     # Total members in the system
    member_count = Member.objects.count()
    
    # Total number of unique Ministries, Communities, and Committees
    ministry_count = Ministry.objects.count()
    community_count = Community.objects.count()
    committee_count = Committee.objects.count()

    context = {
        'member_count': member_count,
        'ministry_count': ministry_count,
        'community_count': community_count,
        'committee_count': committee_count,
        'recent_activities':Member.objects.order_by('-id')[:5]

    }
    return render(request, 'index.html', context)

