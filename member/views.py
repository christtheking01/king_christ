import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db import transaction
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _

from .models import Community, Member, Ministry, CommunityLeader, Zone, CommunityZone, MinistryLeader
from finance.models import TitheReceipt, Offering, EventPledge
from users.models import UserProfile
from .forms import MemberForm, MinistryForm, MinistryLeaderFormSet, ShepherdForm,Committee
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import groupby

# Initialize logger
logger = logging.getLogger('church_app')

@login_required
def table_members(request):
    template = "members/table.html"
    
    # Get filter parameters from request
    community_filter = request.GET.get('community', '')
    
    # Start with active members
    members = Member.objects.all()
    
    # Apply community filter if provided
    if community_filter:
        members = members.filter(shepherd__name__icontains=community_filter)
    
    # Fix: Get profile correctly
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    paginator = Paginator(members, 23)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    grouped_members = []
    current_member = list(page_obj.object_list)
    
    # Sort by shepherd name for grouping
    def get_shepherd_name(member):
        return member.shepherd.name if member.shepherd else ""
    
    current_member.sort(key=get_shepherd_name)
    
    # Group by shepherd
    for shepherd, members in groupby(current_member, key=lambda x: x.shepherd):
        members_list = list(members)
        grouped_members.append({
            'shepherd': shepherd,
            'members': members_list,
            'count': len(members_list)
        })

    shepherds = CommunityLeader.objects.all()
    
    # Get all communities for the filter dropdown
    communities = Community.objects.all().order_by('name')

    context = {
        "profile": profile,
        "grouped_members": grouped_members,
        "page_obj": page_obj,
        "total": paginator.count,
        "shepherds": shepherds,
        "communities": communities,
        "selected_community": community_filter,
        "total_tithe": Member.objects.pays_tithe().count(),
        "total_new_believers": Member.objects.filter(gender='female').count(),
        "total_schooling": Member.objects.schooling().count(),
        "total_working": Member.objects.working().count(),
        "total_delete": Member.objects.filter(active=False).count(),
        "status": "all",
    }
    
    return render(request, template, context)


@login_required
def thumbnail_members(request):
    template = "members/thumbnail.html"
    members = Member.objects.active()
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    profile = UserProfile.objects.get_or_create(user=request.user)
    context = {"members": members, "members_active_list": "active", "ministries": ministries, "shepherds": shepherds, "profile": profile}
    return render(request, template, context)


@login_required
def list_members(request):
    template = "members/list.html"
    
    # Get search query (template uses 'search' parameter)
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    gender_filter = request.GET.get('gender', '')
    
    # Get all members ordered by shepherd and name
    all_members = Member.objects.active()
    
    # Apply search filter
    if search_query:
        all_members = all_members.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(telephone__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(shepherd__name__icontains=search_query) |
            Q(ministry__name__icontains=search_query) |
            Q(guardians_name__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter == 'active':
        all_members = all_members.filter(active=True)
    elif status_filter == 'inactive':
        all_members = all_members.filter(active=False)
    
    # Apply gender filter
    if gender_filter:
        all_members = all_members.filter(gender=gender_filter)
    
    # Order the results
    all_members = all_members.order_by('shepherd__name', 'name')
    
    # Create paginator with 23 items per page
    paginator = Paginator(all_members, 23)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Group members on current page by shepherd
    grouped_members = []
    current_members = list(page_obj.object_list)
    
    # Sort by shepherd name for grouping
    def get_shepherd_name(member):
        return member.shepherd.name if member.shepherd else ""
    
    current_members.sort(key=get_shepherd_name)
    
    # Group by shepherd
    for shepherd, members in groupby(current_members, key=lambda x: x.shepherd):
        members_list = list(members)
        grouped_members.append({
            'shepherd': shepherd,
            'members': members_list,
            'count': len(members_list)
        })
    
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        "profile": profile,
        "grouped_members": grouped_members,
        "members": page_obj.object_list,  # Add simple members list for template
        "page_obj": page_obj,
        "shepherds": shepherds, 
        "ministries": ministries, 
        "total": paginator.count,
        "total_members": paginator.count,  
        "active_members": Member.objects.active().count(),  
        "total_tithe": Member.objects.pays_tithe().count(),
        "total_new_believers": Member.objects.filter(gender='female').count(),
        "total_schooling": Member.objects.schooling().count(),
        "total_working": Member.objects.working().count(),
        "total_delete": Member.objects.filter(active=False).count(),
        "status": "all",
        "search_query": search_query,  
    }
    
    return render(request, template, context)

@login_required
def list_deleted_members(request):
    template = "members/list.html"
    members = Member.objects.deleted()
    shepherds = Community.objects.all()
    ministries = Ministry.objects.all()
    profile = UserProfile.objects.get_or_create(user=request.user)
    context = {
        "profile": profile,
        "members": members, "shepherds": shepherds, "ministries": ministries, "total": len(members),
        "total_tithe": len(Member.objects.pays_tithe()),
        "total_new_believers": len(Member.objects.filter(gender='female')),
        "total_schooling": len(Member.objects.schooling()),
        "total_working": len(Member.objects.working()),
        "total_delete": len(members),
        "status": "all",
        "active": "active"
    }
    return render(request, template, context)


@login_required
def detail_member(request, pk):
    template = "members/detail.html"
    member = get_object_or_404(Member, pk=pk)
    profile = UserProfile.objects.get_or_create(user=request.user)
    
    # Get member's committees
    committees = Committee.objects.filter(member=member)
    
    # Get tithe payment history
    tithe_receipts = TitheReceipt.objects.filter(member=member).order_by('-date')[:10]
    
    # Get offerings (both registered member offerings and anonymous with matching name)
    offerings = Offering.objects.filter(
        Q(member=member) | 
        Q(donor_name__iexact=member.name, is_anonymous=False)
    ).order_by('-date')[:10]
    
    # Get event pledges
    pledges = EventPledge.objects.filter(member=member).order_by('-created_at')[:10]
    
    # Calculate payment statistics
    total_tithe = sum(t.amount for t in tithe_receipts)
    total_offerings = sum(o.amount for o in offerings)
    total_pledged = sum(p.promised_amount for p in pledges)
    total_paid_pledges = sum(p.paid_amount for p in pledges)
    
    context = {
        "member": member,
        "profile": profile,
        "committees": committees,
        "tithe_receipts": tithe_receipts,
        "offerings": offerings,
        "pledges": pledges,
        "payment_stats": {
            "total_tithe": total_tithe,
            "total_offerings": total_offerings,
            "total_pledged": total_pledged,
            "total_paid_pledges": total_paid_pledges,
            "pledge_balance": total_pledged - total_paid_pledges,
        }
    }
    return render(request, template, context)

@login_required
def edit_member(request, pk):
    template = "members/edit.html"
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == "POST":
        # Log form submission for audit trail
        logger.info("Member update POST received for member %s by user %s", pk, request.user.username)
        
        form = MemberForm(request.POST, request.FILES, instance=member)
        
        if form.is_valid():
            form.save()
            messages.success(request, _("Member Information Updated Successfully"))
            return redirect("list_members")
        else:
            # Log form errors for debugging
            logger.warning("Member update form errors for member %s: %s", pk, form.errors)
            
            # Show specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # Re-render form with errors
            communities = Community.objects.all()
            ministries = Ministry.objects.all()
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            context = {
                "member": member, 
                "form": form, 
                "communityleader": communities,  
                "ministries": ministries, 
                "profile": profile
            }
            return render(request, template, context)
    else:
        # GET request - show edit form
        # Create form with instance
        form = MemberForm(instance=member)
        
        # Log form field access for debugging
        logger.debug("Form fields accessed for member %s: %s", member.id, list(form.fields.keys()))
        
        communities = Community.objects.all()
        ministries = Ministry.objects.all()
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        context = {
            "member": member, 
            "form": form, 
            "communityleader": communities,  
            "ministries": ministries, 
            "profile": profile
        }
        return render(request, template, context)

@login_required
def delete_member(request, pk):
    # TODO: Make this functionality available only to admins
    member = get_object_or_404(Member, pk=pk)
    member.active = False
    member.save()
    messages.success(request, _("Member Deleted Successfully"))
    return redirect("list_members")


@login_required
def restore_member(request, pk):
    # TODO: Make this functionality available only to admins
    member = get_object_or_404(Member, pk=pk)
    member.active = True
    member.save()
    messages.success(request, _("Member Restored Successfully"))
    return redirect("list_members")


@login_required
def search_members(request):
    template = "members/list.html"
    q = request.GET.get('q')
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    profile = UserProfile.objects.get_or_create(user=request.user)
    context = {"ministries": ministries, "shepherds": shepherds, "profile": profile}
    if q != '':
        qs = Member.objects.active().filter(
            Q(name__icontains=q) | Q(shepherd__name__icontains=q) | Q(ministry__name__icontains=q)|
            Q(location__icontains=q) | Q(fathers_name__contains=q) | Q(mothers_name__contains=q)
        )
        context["members"] = qs
        context['total'] = len(qs)
        return render(request, template, context)
    else:
        members = Member.objects.active()
        context['members'] = members
        context['total'] = len(members)
        return render(request, template, context)


@login_required
def get_members_by_statuses(request, status):
    template = "members/list.html"
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    profile = UserProfile.objects.get_or_create(user=request.user)
    members = None
    if status == "tithe":
        members = Member.objects.pays_tithe()
    elif status == "new_believers":
        members = Member.objects.filter(gender='female')
    elif status == "working":
        members = Member.objects.working()
    elif status == "schooling":
        members = Member.objects.schooling()

    context = {
        "profile": profile,
        "members": members,
        "shepherds": shepherds,
        "ministries": ministries,
        "total": len(Member.objects.active()),
        "total_tithe": len(Member.objects.pays_tithe()),
        "total_new_believers": len(Member.objects.filter(gender='female')),
        "total_schooling": len(Member.objects.schooling()),
        "total_working": len(Member.objects.working()),
        "total_delete": len(Member.objects.deleted()),
        status: status,
    }
    return render(request, template, context)


@login_required
def get_members_by_shepherds(request, shepherd):
    template = "members/list.html"
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    members = Member.objects.active().filter(shepherd__name__icontains=shepherd)
    profile = UserProfile.objects.get_or_create(user=request.user)
    context = {
        "profile": profile,
        "members": members,
        "shepherds": shepherds,
        "ministries": ministries,
        "total": len(Member.objects.active()),
        "total_tithe": len(Member.objects.pays_tithe()),
        "total_new_believers": len(Member.objects.filter(gender='female')),
        "total_schooling": len(Member.objects.schooling()),
        "total_working": len(Member.objects.working()),
        "total_delete": len(Member.objects.deleted()),
        "shepherd_name": shepherd
    }

    return render(request, template, context)


@login_required
def filter_members(request):
    template = "members/thumbnail.html"
    shepherds = CommunityLeader.objects.all()
    ministries = Ministry.objects.all()
    initial_members = Member.objects.active()
    statuses = []
    for i in request.GET:
        if request.GET.get(i) == 'on':
            statuses.append(i)
    for i in statuses:
        if i == 'pays_tithe':
            initial_members = initial_members.filter(pays_tithe=True)
        elif i == 'working':
            initial_members = initial_members.filter(working=True)
        elif i == 'schooling':
            initial_members = initial_members.filter(schooling=True)
        elif i == "new_believer_school":
            initial_members = initial_members.filter(gender='female')
    # import pdb; pdb.set_trace()

    ministry = request.GET.get('ministry')
    profile = UserProfile.objects.get_or_create(user=request.user)

    context = {
        "profile": profile,
        "members": initial_members,
        "shepherds": shepherds,
        "ministries": ministries,
        "total": len(Member.objects.active()),
        "total_tithe": len(Member.objects.pays_tithe()),
        "total_new_believers": len(Member.objects.filter(gender='female')),
        "total_schooling": len(Member.objects.schooling()),
        "total_working": len(Member.objects.working()),
        ministry: ministry
    }
    if ministry is not None:
        initial_members = initial_members.filter(ministry__name__icontains=ministry)
        context['members'] = initial_members
        context['id_ministry'] = ministry

    shepherd = request.GET.get('shepherd')
    if shepherd is not None:
        initial_members = initial_members.filter(shepherd__name__icontains=shepherd)
        # import pdb; pdb.set_trace()
        context['members'] = initial_members

    for i in statuses:
        context[i] = 'checked'

    return render(request, template, context)


from django.views.generic import CreateView, ListView, TemplateView
from django.urls import reverse_lazy

class BaseMemberView:
    template_name = 'members/add.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add mode to context to differentiate between single and multiple
        context['mode'] = getattr(self, 'mode', 'single')
        return context

# Single member creation view

class AddMemberView(BaseMemberView, CreateView):
    model = Member
    form_class = MemberForm
    success_url = reverse_lazy('table_members')
    mode = 'single'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shepherds'] = Community.objects.all()
        context['ministries'] = Ministry.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def form_valid(self,form):
        messages.success(self.request, _('Member added successfully!'))
        profile = UserProfile.objects.get_or_create(user=self.request.user)
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)

# Multiple members creation view
class CreateMembersView(BaseMemberView, TemplateView):
    mode = 'multiple'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add 3 empty forms for multiple member creation
        context['form1'] = MemberForm(prefix='form1')
        context['form2'] = MemberForm(prefix='form2')
        context['form3'] = MemberForm(prefix='form3')
        # Add context for dropdowns
        context['shepherds'] = Community.objects.all()
        context['ministries'] = Ministry.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        # Handle dynamic multi-member form
        saved_count = 0
        errors = []
        
        # Find all member data from the form
        member_data = {}
        for key, value in request.POST.items():
            if key.startswith('name_') and value.strip():
                member_num = key.split('_')[1]
                member_data[member_num] = {}
        
        # Process each member
        for member_num in member_data.keys():
            member_fields = {}
            
            # Collect all fields for this member
            for field_name in ['name', 'code', 'telephone', 'gender', 'location', 'shepherd', 'ministry']:
                field_key = f"{field_name}_{member_num}"
                # Handle searchable select fields (they have _id suffix)
                if field_name in ['shepherd', 'ministry']:
                    id_field_key = f"{field_name}_{member_num}_id"
                    if id_field_key in request.POST:
                        member_fields[field_name] = request.POST[id_field_key]
                elif field_key in request.POST:
                    member_fields[field_name] = request.POST[field_key]
            
            # Handle file uploads
            picture_key = f"picture_{member_num}"
            if picture_key in request.FILES:
                member_fields['picture'] = request.FILES[picture_key]
            
            # Create and validate form
            if member_fields.get('name'):
                form = MemberForm(member_fields)
                if form.is_valid():
                    try:
                        form.save()
                        saved_count += 1
                    except Exception as e:
                        errors.append(f"Error saving member {member_num}: {str(e)}")
                else:
                    errors.append(f"Invalid data for member {member_num}: {form.errors}")
        
        if saved_count > 0:
            success_msg = _('Successfully added %(count)s member(s)!') % {'count': saved_count}
            if errors:
                success_msg += f" Some errors occurred: {', '.join(errors[:3])}"
            messages.success(request, success_msg)
            return redirect('list_members')
        else:
            if errors:
                messages.error(request, _('No members were saved. Errors: %(errors)s') % {'errors': ', '.join(errors[:3])})
            else:
                messages.error(request, _('No valid member data provided. Please fill at least the name field for each member.'))
            return redirect('create_member')

@login_required
class MemberListView(ListView):
    model = Member
    template_name = 'members/table.html'
    context_object_name = 'members'
    paginate_by = 20

#Committees Views

@login_required
def list_committees(request):
    committees = Committee.objects.all().order_by('Commitee_name')
    return render(request, 'committees/list.html', {
        'committees': committees,
        'committee_active_list': True
    })

@login_required
def create_committee(request):
    if request.method == 'POST':
        comm_name = request.POST.get('Commitee_name')
        desc = request.POST.get('description')
        
        # Get dynamic lists
        member_names = request.POST.getlist('members[]')
        positions = request.POST.getlist('positions[]')
        phones = request.POST.getlist('phones[]')

        for m_name, pos, ph in zip(member_names, positions, phones):
            if m_name and pos:
                try:
                    # Look up member by name (since Datalist sends text)
                    member_obj = Member.objects.get(name=m_name)
                    
                    # Unique Position Check
                    if Committee.objects.filter(Commitee_name=comm_name, position=pos).exists():
                        messages.error(request, _("The position %(position)s is already taken.") % {'position': pos})
                        continue

                    Committee.objects.create(
                        Commitee_name=comm_name,
                        description=desc,
                        member=member_obj,
                        position=pos,
                        phone=ph
                    )
                except Member.DoesNotExist:
                    messages.error(request, _("Member '%(name)s' not found.") % {'name': m_name})

        messages.success(request, _("Committee created successfully!"))
        return redirect('list_committees')

    # Pass data to template
    context = {
        'members': Member.objects.all(),
        'positions': Committee.Position,
        'committee_active_add': True
    }
    return render(request, 'committees/create.html', context)

@login_required
def edit_committee(request, name):
    # Get all records sharing the same committee name
    committee_members = Committee.objects.filter(Commitee_name=name)
    if request.method == 'POST':
        committee_members.delete() # Simple update strategy: replace records
        # Re-use the creation logic here...
        return redirect('list_committees')
        
    context = {
        'name': name,
        'committee_members': committee_members,
        'members': Member.objects.all(),
        'positions': Committee.Position,
        'desc': committee_members.first().description if committee_members.exists() else ""
    }
    return render(request, 'committees/edit.html', context)

@login_required
def delete_committee_member(request, pk):
    member = get_object_or_404(Committee, pk=pk)
    name = member.Commitee_name
    member.delete()
    messages.success(request, _("Member removed from committee."))
    return redirect('list_committees')

"""
ministries views 
"""

@login_required
def create_ministry(request):
    if request.method == 'POST':
        ministry_form = MinistryForm(request.POST)
        leader_formset = MinistryLeaderFormSet(request.POST)
        
        if ministry_form.is_valid() and leader_formset.is_valid():
            try:
                with transaction.atomic():
                    ministry = ministry_form.save()
                    leader_formset.instance = ministry
                    leader_formset.save()
                    
                messages.success(request, _('Ministry "%(name)s" has been created successfully!') % {'name': ministry.name})
                return redirect('ministry_detail', pk=ministry.pk)
            except Exception as e:
                messages.error(request, _('Error creating ministry: %(error)s') % {'error': str(e)})
        else:
            messages.error(request, _('Please correct the errors below.'))
    else:
        ministry_form = MinistryForm()
        leader_formset = MinistryLeaderFormSet()
    
    context = {
        'ministry_form': ministry_form,
        'leader_formset': leader_formset,
        'members': Member.objects.filter(active=True).order_by('name'),
        'title': 'Create Ministry'
    }
    return render(request, 'ministries/ministry_form.html', context)

@login_required
def create_minis(request):
    if request.method == 'POST':
        ministry_form = MinistryForm(request.POST)
        leader_formset = MinistryLeaderFormSet(request.POST)

        member_names = request.POST.getlist('members[]')
        positions = request.POST.getlist('positions[]')
        phones = request.POST.getlist('phones[]')

        if ministry_form.is_valid() and leader_formset.is_valid():
            with transaction.atomic():
                    ministry = ministry_form.save()

                    for m_name, pos, ph in zip(member_names,positions,phones):
                        if m_name and pos:
                            try:
                                # Look up member by name (since Datalist sends text)
                                member_obj = Member.objects.get(name=m_name)
                                
                                # Unique Position Check
                                if Committee.objects.filter(position=pos).exists():
                                    messages.error(request, _("The position %(position)s is already taken.") % {'position': pos})
                                    continue

                                MinistryLeader.objects.create(
                                    member=member_obj,
                                    position=pos,
                                    phone=ph
                                )
                            except Member.DoesNotExist:
                                messages.error(request, _("Member '%(name)s' not found.") % {'name': m_name})

                    messages.success(request, _("Ministry created successfully!"))
                    return redirect('ministry_detail')
        else:
            ministry_form = MinistryForm()
            leader_formset = MinistryLeaderFormSet()
        context = {
            ministry_form:'ministry_Form',
            leader_formset:'leader_formset',
            'tittle':'create ministry'
        }
        
        return render(request, 'ministries/ministry_form.html', context)





@login_required
def update_ministry(request, pk):
    ministry = get_object_or_404(Ministry, pk=pk)
    
    if request.method == 'POST':
        ministry_form = MinistryForm(request.POST, instance=ministry)
        leader_formset = MinistryLeaderFormSet(request.POST, instance=ministry)
        
        if ministry_form.is_valid() and leader_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save ministry
                    ministry = ministry_form.save()
                    
                    # Save leaders
                    leaders = leader_formset.save(commit=False)
                    
                    # Save new and updated leaders
                    for leader in leaders:
                        leader.ministry = ministry
                        leader.save()
                    
                    # Delete leaders marked for deletion
                    for leader in leader_formset.deleted_objects:
                        leader.delete()
                    
                    messages.success(
                        request, 
                        _('Ministry "%(name)s" has been updated successfully!') % {'name': ministry.name}
                    )
                    return redirect('ministry_detail', pk=ministry.pk)
                    
            except Exception as e:
                messages.error(request, _('Error updating ministry: %(error)s') % {'error': str(e)})
        else:
            # Display specific form errors
            if ministry_form.errors:
                for field, errors in ministry_form.errors.items():
                    for error in errors:
                        messages.error(request, _('%(field)s: %(error)s') % {'field': field, 'error': error})
            
            if leader_formset.errors:
                for i, form_errors in enumerate(leader_formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            for error in errors:
                                messages.error(request, _('Leader %(num)s - %(field)s: %(error)s') % {'num': i+1, 'field': field, 'error': error})
            
            if leader_formset.non_form_errors():
                for error in leader_formset.non_form_errors():
                    messages.error(request, _(error))
    else:
        ministry_form = MinistryForm(instance=ministry)
        leader_formset = MinistryLeaderFormSet(instance=ministry)
    
    context = {
        'ministry_form': ministry_form,
        'leader_formset': leader_formset,
        'members': Member.objects.filter(active=True).order_by('name'),
        'ministry': ministry,
        'title': f'Update {ministry.name}',
        'is_update': True
    }
    return render(request, 'ministries/ministry_form.html', context)


@login_required
def ministry_list(request):
    ministries = Ministry.objects.all().prefetch_related('leaders', 'leaders__community')
    context = {
        'ministries': ministries,
        'title': 'Ministries'
    }
    return render(request, 'ministries/ministry_list.html', context)


@login_required
def ministry_detail(request, pk):
    ministry = get_object_or_404(Ministry, pk=pk)
    leaders = ministry.leaders.filter(is_active=True).select_related('community')
    
    context = {
        'ministry': ministry,
        'leaders': leaders,
        'title': ministry.name
    }
    return render(request, 'ministries/ministry_detail.html', context)


@login_required
def delete_ministry(request, pk):
    ministry = get_object_or_404(Ministry, pk=pk)
    
    if request.method == 'POST':
        ministry_name = ministry.name
        ministry.delete()
        messages.success(request, _('Ministry "%(name)s" has been deleted successfully!') % {'name': ministry_name})
        return redirect('ministry_list')
    
    context = {
        'ministry': ministry,
        'title': 'Delete Ministry'
    }
    return render(request, 'ministries/ministry_confirm_delete.html', context)

@login_required
def list_shepherds(request):
    template = "shepherds/list.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    
    # Get all communities with their leaders and members
    communities = Community.objects.prefetch_related('leaders').all()

    # Build list of communities with their members
    communities_with_members = []
    total_members = 0
    total_leaders = 0
    unassigned_roles = 0

    for community in communities:
        members = Member.objects.filter(shepherd=community, active=True).order_by('name')
        communities_with_members.append({
            'community': community,
            'members': members,
            'member_count': members.count()
        })
        total_members += members.count()
        total_leaders += community.leaders.count()

    # Calculate unfilled roles (expected 5 main roles: Chair, Vice Chair, Secretary, Vice Secretary, Accountant)
    expected_roles = 5
    for item in communities_with_members:
        filled_roles = item['community'].leaders.filter(
            leader__in=['CHAIR PERSON', 'CHAIRPERSON', 'VICE CHAIR', 'SECRETARY', 'VICE SECRETARY', 'ACCOUNTANT']
        ).count()
        unassigned_roles += max(0, expected_roles - filled_roles)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(communities_with_members, 10)  # 10 communities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "communities_with_members": page_obj,
        "shepherds_active_list": "active",
        "profile": profile,
        # Stats
        "total_communities": communities.count(),
        "total_leaders": total_leaders,
        "total_members": total_members,
        "unassigned_roles": unassigned_roles,
    }
    return render(request, template, context)

@login_required
def add_shepherd(request):
    template = "shepherds/add.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    
    # Get existing communities for dropdown
    communities = Community.objects.all()
    
    context = {
        "communities": communities,
        "shepherds_active_add": "active", 
        "profile": profile
    }
    return render(request, template, context)

@login_required
def create_shepherd(request):
    if request.method == "POST":
        community_name = request.POST.get('community_name')
        leader_names = request.POST.getlist('leaders_name[]')
        leader_positions = request.POST.getlist('leaders_position[]')
        leader_descriptions = request.POST.getlist('leaders_description[]')
        leader_phones = request.POST.getlist('leaders_phone[]')
        
        logger.info("Processing %s leaders for community: %s by user %s", len(leader_names), community_name, request.user.username)
        
        # Validate required fields
        if not community_name:
            messages.error(request, "Community name is required")
            return redirect('add_shepherd')
        
        if not leader_names or not any(leader_names):
            messages.error(request, "Please add at least one leader")
            return redirect('add_shepherd')
        
        success_count = 0
        error_messages = []
        
        try:
            # Get or create the Community object
            community, created = Community.objects.get_or_create(name=community_name)
            if created:
                logger.info("Created new community: %s", community_name)
            else:
                logger.info("Using existing community: %s", community_name)
        except Exception as e:
            messages.error(request, f"Error with community: {str(e)}")
            return redirect('add_shepherd')
        
        # Process each leader
        for i in range(len(leader_names)):
            # Skip empty entries
            if not leader_names[i] or not leader_positions[i]:
                continue
            
            # Check if position already exists in this community
            existing_leader = CommunityLeader.objects.filter(
                community_name=community,  # Use the Community object, not string
                leader=leader_positions[i]
            ).first()
            
            if existing_leader:
                error_messages.append(
                    f"Position '{leader_positions[i]}' is already assigned to {existing_leader.name} in {community_name}"
                )
                continue
            
            try:
                # Create the leader with Community object
                leader = CommunityLeader(
                    community_name=community,  # Pass the Community object
                    name=leader_names[i],
                    leader=leader_positions[i],
                    description=leader_descriptions[i] if i < len(leader_descriptions) else '',
                    phone=leader_phones[i] if i < len(leader_phones) else ''
                )
                
                leader.save()
                success_count += 1
                logger.info("Created leader %s as %s in community %s", leader_names[i], leader_positions[i], community_name)
                
                # Auto-create Member record for this leader
                member_phone = leader_phones[i] if i < len(leader_phones) else None
                member, member_created = Member.objects.get_or_create(
                    name=leader_names[i],
                    defaults={
                        'shepherd': community,
                        'telephone': member_phone,
                        'active': True,
                        'location': community.name,
                    }
                )
                if member_created:
                    logger.info("Created member record for leader: %s", leader_names[i])
                
            except Exception as e:
                error_msg = f"Error creating {leader_names[i]}: {str(e)}"
                error_messages.append(error_msg)
                logger.error("Exception creating leader %s: %s", leader_names[i], str(e))
        
        # Display results
        if success_count > 0:
            messages.success(request, f"Successfully added {success_count} leader(s) to {community_name}")
        
        for error in error_messages:
            messages.error(request, error)
        
        if success_count == 0 and error_messages:
            return redirect('add_shepherd')
        else:
            return redirect('list_shepherds')
    
    return redirect('add_shepherd')


@login_required
def edit_community(request, community_id):
    template = "shepherds/edit_community.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    
    try:
        community = Community.objects.get(id=community_id)
        leaders = community.leaders.all()
    except Community.DoesNotExist:
        messages.error(request, "Community not found")
        return redirect('list_shepherds')
    
    if request.method == "POST":
        community_name = request.POST.get('community_name')
        
        if not community_name:
            messages.error(request, "Community name is required")
            return redirect('edit_community', community_id=community_id)
        
        # Update community name
        community.name = community_name
        community.save()
        
        # Update leaders if provided
        leader_ids = request.POST.getlist('leader_ids[]')
        leader_names = request.POST.getlist('leader_names[]')
        leader_positions = request.POST.getlist('leader_positions[]')
        leader_descriptions = request.POST.getlist('leader_descriptions[]')
        leader_phones = request.POST.getlist('leader_phones[]')
        
        # Track used positions to prevent duplicates
        used_positions = set()
        error_messages = []
        
        # Update existing leaders
        for i, leader_id in enumerate(leader_ids):
            if i >= len(leader_names) or i >= len(leader_positions):
                continue
                
            position = leader_positions[i]
            
            # Check for duplicate positions in the form data
            if position in used_positions:
                error_messages.append(f"Duplicate position '{position}' detected. Each position can only be assigned once.")
                continue
            
            # Check if another leader already has this position (excluding current leader)
            existing = CommunityLeader.objects.filter(
                community_name=community,
                leader=position
            ).exclude(id=leader_id).first()
            
            if existing:
                error_messages.append(f"Position '{position}' is already assigned to {existing.name}")
                continue
            
            used_positions.add(position)
            
            try:
                leader = CommunityLeader.objects.get(id=leader_id, community_name=community)
                leader.name = leader_names[i]
                leader.leader = position
                if i < len(leader_descriptions):
                    leader.description = leader_descriptions[i]
                if i < len(leader_phones):
                    leader.phone = leader_phones[i]
                leader.save()
            except CommunityLeader.DoesNotExist:
                continue
        
        if error_messages:
            for error in error_messages:
                messages.error(request, error)
        else:
            messages.success(request, f"Community '{community_name}' updated successfully")
        
        return redirect('list_shepherds')
    
    # Get community members for leader selection dropdown
    community_members_list = Member.objects.filter(shepherd=community, active=True).order_by('name')
    
    context = {
        "community": community,
        "leaders": leaders,
        "community_members": community_members_list,
        "shepherds_active_list": "active", 
        "profile": profile
    }
    return render(request, template, context)


@login_required
def delete_community(request, community_id):
    if request.method == "POST":
        try:
            community = Community.objects.get(id=community_id)
            community_name = community.name
            community.delete()
            messages.success(request, f"Community '{community_name}' deleted successfully")
        except Community.DoesNotExist:
            messages.error(request, "Community not found")
    
    return redirect('list_shepherds')


# ================================================================================= #
#                                   Zone Views                                      #
# ================================================================================= #

@login_required
def list_zones(request):
    """List all zones with their communities, leaders and member counts"""
    template = "zones/list.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    zones = Zone.objects.prefetch_related('community_zones__community', 'leaders').all()

    context = {
        "zones": zones,
        "profile": profile,
        "zones_active_list": "active",
    }
    return render(request, template, context)


@login_required
def zone_detail(request, pk):
    """Show zone details with all communities, leaders and their members"""
    template = "zones/detail.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    zone = get_object_or_404(Zone, pk=pk)

    # Get zone leaders
    zone_leaders = zone.leaders.filter(is_active=True).order_by('position')

    # Get communities in this zone with their members
    community_zones = CommunityZone.objects.filter(zone=zone).select_related('community')
    communities_data = []

    for cz in community_zones:
        community = cz.community
        members = community.get_members()
        communities_data.append({
            'community': community,
            'members': members,
            'member_count': members.count()
        })

    context = {
        "zone": zone,
        "zone_leaders": zone_leaders,
        "communities_data": communities_data,
        "total_communities": zone.get_communities_count(),
        "total_members": zone.get_total_members(),
        "profile": profile,
    }
    return render(request, template, context)


@login_required
def create_zone(request):
    """Create a new zone with leaders"""
    template = "zones/create.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    communities = Community.objects.all().order_by('name')

    if request.method == "POST":
        zone_name = request.POST.get('zone_name')
        description = request.POST.get('description')
        community_ids = request.POST.getlist('communities[]')
        
        # Get leader data
        leader_names = request.POST.getlist('leader_names[]')
        leader_positions = request.POST.getlist('leader_positions[]')
        leader_phones = request.POST.getlist('leader_phones[]')
        leader_emails = request.POST.getlist('leader_emails[]')

        if not zone_name:
            messages.error(request, "Zone name is required")
            return redirect('create_zone')

        try:
            # Create the zone
            zone = Zone.objects.create(
                name=zone_name,
                description=description or None
            )

            # Add communities to the zone
            for community_id in community_ids:
                if community_id:
                    try:
                        community = Community.objects.get(id=community_id)
                        CommunityZone.objects.create(zone=zone, community=community)
                    except Community.DoesNotExist:
                        continue

            # Create zone leaders
            for i in range(len(leader_names)):
                if leader_names[i] and leader_positions[i]:
                    ZoneLeader.objects.create(
                        zone=zone,
                        name=leader_names[i],
                        position=leader_positions[i],
                        phone=leader_phones[i] if i < len(leader_phones) else None,
                        email=leader_emails[i] if i < len(leader_emails) else None
                    )

            messages.success(request, f"Zone '{zone_name}' created successfully!")
            return redirect('list_zones')

        except Exception as e:
            messages.error(request, f"Error creating zone: {str(e)}")

    context = {
        "communities": communities,
        "profile": profile,
        "zones_active_add": "active",
    }
    return render(request, template, context)


@login_required
def edit_zone(request, pk):
    """Edit an existing zone with leaders"""
    template = "zones/edit.html"
    profile = UserProfile.objects.get_or_create(user=request.user)
    zone = get_object_or_404(Zone, pk=pk)
    communities = Community.objects.all().order_by('name')
    assigned_community_ids = list(CommunityZone.objects.filter(zone=zone).values_list('community_id', flat=True))
    
    # Get zone leaders and zone members for dropdown
    zone_leaders = zone.leaders.filter(is_active=True).order_by('position')
    zone_communities = zone.get_communities()
    zone_members = Member.objects.filter(shepherd__in=zone_communities, active=True).order_by('name')

    if request.method == "POST":
        zone.name = request.POST.get('zone_name')
        zone.description = request.POST.get('description') or None
        zone.save()

        # Update communities
        new_community_ids = request.POST.getlist('communities[]')

        # Remove unselected communities
        CommunityZone.objects.filter(zone=zone).exclude(community_id__in=new_community_ids).delete()

        # Add new communities
        for community_id in new_community_ids:
            if community_id:
                CommunityZone.objects.get_or_create(zone=zone, community_id=community_id)
        
        # Update zone leaders
        leader_ids = request.POST.getlist('leader_ids[]')
        leader_names = request.POST.getlist('leader_names[]')
        leader_positions = request.POST.getlist('leader_positions[]')
        leader_phones = request.POST.getlist('leader_phones[]')
        leader_emails = request.POST.getlist('leader_emails[]')
        
        # Update existing leaders
        for i, leader_id in enumerate(leader_ids):
            try:
                leader = ZoneLeader.objects.get(id=leader_id, zone=zone)
                if i < len(leader_names):
                    leader.name = leader_names[i]
                if i < len(leader_positions):
                    leader.position = leader_positions[i]
                if i < len(leader_phones):
                    leader.phone = leader_phones[i]
                if i < len(leader_emails):
                    leader.email = leader_emails[i]
                leader.save()
            except ZoneLeader.DoesNotExist:
                continue

        messages.success(request, f"Zone '{zone.name}' updated successfully!")
        return redirect('list_zones')

    context = {
        "zone": zone,
        "zone_leaders": zone_leaders,
        "zone_members": zone_members,
        "communities": communities,
        "assigned_community_ids": assigned_community_ids,
        "profile": profile,
    }
    return render(request, template, context)


@login_required
def delete_zone(request, pk):
    """Delete a zone"""
    if request.method == "POST":
        zone = get_object_or_404(Zone, pk=pk)
        zone_name = zone.name
        zone.delete()
        messages.success(request, f"Zone '{zone_name}' deleted successfully!")
    return redirect('list_zones')


# ================================================================================= #
#                                   API View Functions                              #
# ================================================================================= #

@login_required
def api_get_members(request):
    """API endpoint to get members - requires authentication."""
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated API access attempt to api_get_members from IP: %s", request.META.get('REMOTE_ADDR'))
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    members = Member.objects.active()
    shepherds = CommunityLeader.objects.all()
    ministry = Ministry.objects.all()
    data = {
        "STATUS": "OK",
        "members": list(members.values('id', 'name', 'code', 'telephone', 'shepherd__name')),
        "shepherds": list(shepherds.values('id', 'name', 'leader', 'phone')),
        "ministry": list(ministry.values('id', 'name'))
    }
    logger.info("API get_members accessed by user: %s", request.user.username)
    return JsonResponse(data, content_type="application/json")


@login_required
def api_create_member(request):
    """API endpoint to create member - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    form = MemberForm(request.POST, request.FILES or None)
    if form.is_valid():
        member = form.save(commit=False)
        member.save()
        logger.info("Member created via API by user %s: %s", request.user.username, member.name)
        return JsonResponse({"STATUS": "OK", "MEMBER_ID": member.pk}, content_type="application/json")
    else:
        logger.warning("Invalid member creation attempt by user %s: %s", request.user.username, form.errors)
        return JsonResponse({"STATUS": "INVALID", "ERRORS": dict(form.errors)}, status=400)


@login_required
def api_get_shepherds(request):
    """API endpoint to get shepherds - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    shepherds = CommunityLeader.objects.all()
    data = {"STATUS": "OK", "shepherds": list(shepherds.values('id', 'name', 'leader', 'phone', 'community_name__name'))}
    return JsonResponse(data, content_type="application/json")


@login_required
def api_create_shepherd(request):
    """API endpoint to create shepherd - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    form = ShepherdForm(request.POST, request.FILES or None)
    if form.is_valid():
        shepherd = form.save(commit=False)
        shepherd.save()
        logger.info("Shepherd created via API by user %s: %s", request.user.username, shepherd.name)
        return JsonResponse({"STATUS": "OK", "SHEPHERD_ID": shepherd.pk}, content_type="application/json")
    else:
        return JsonResponse({"STATUS": "INVALID", "ERRORS": dict(form.errors)}, status=400)


@login_required
def api_edit_shepherd(request, pk):
    """API endpoint to edit shepherd - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    shepherd = get_object_or_404(CommunityLeader, pk=pk)
    form = ShepherdForm(request.POST or None, instance=shepherd)
    if form.is_valid():
        form.save()
        logger.info("Shepherd edited via API by user %s: %s", request.user.username, shepherd.name)
        return JsonResponse({"STATUS": "OK", "CODE": 0}, content_type="application/json")
    else:
        return JsonResponse({"STATUS": "INVALID", "CODE": -1, "ERRORS": dict(form.errors)}, status=400)


@login_required
def api_delete_shepherd(request, pk):
    """API endpoint to delete shepherd - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    shepherd = get_object_or_404(CommunityLeader, pk=pk)
    shepherd_name = shepherd.name
    shepherd.delete()
    logger.info("Shepherd deleted via API by user %s: %s", request.user.username, shepherd_name)
    return JsonResponse({"STATUS": "OK", "CODE": 0}, content_type="application/json")


@login_required
def api_get_ministry(request):
    """API endpoint to get all ministries - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    ministries = Ministry.objects.all()
    data = {"STATUS": "OK", "ministries": list(ministries.values('id', 'name', 'description'))}
    return JsonResponse(data, content_type="application/json")


@login_required
def api_create_ministry(request):
    """API endpoint to create ministry - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    form = MinistryForm(request.POST, request.FILES or None)
    if form.is_valid():
        ministry = form.save(commit=False)
        ministry.save()
        logger.info("Ministry created via API by user %s: %s", request.user.username, ministry.name)
        return JsonResponse({"STATUS": "OK", "MINISTRY_ID": ministry.pk}, content_type="application/json")
    else:
        return JsonResponse({"STATUS": "INVALID", "ERRORS": dict(form.errors)}, status=400)


@login_required
def api_edit_ministry(request, pk):
    """API endpoint to edit ministry - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    ministry = get_object_or_404(Ministry, pk=pk)
    form = MinistryForm(request.POST or None, instance=ministry)
    if form.is_valid():
        form.save()
        logger.info("Ministry edited via API by user %s: %s", request.user.username, ministry.name)
        return JsonResponse({"STATUS": "OK", "CODE": 0}, content_type="application/json")
    else:
        return JsonResponse({"STATUS": "INVALID", "ERRORS": dict(form.errors)}, status=400)


@login_required
def api_delete_ministry(request, pk):
    """API endpoint to delete ministry - requires authentication."""
    if not request.user.is_authenticated:
        return JsonResponse({"STATUS": "INVALID", "ERROR_TYPE": "AUTHENTICATION REQUIRED", "STATUS_CODE": 401}, status=401)
    if request.method != "POST":
        return JsonResponse({"STATUS": "INVALID", "ERROR": "POST method required"}, status=405)
    ministry = get_object_or_404(Ministry, pk=pk)
    ministry_name = ministry.name
    ministry.delete()
    logger.info("Ministry deleted via API by user %s: %s", request.user.username, ministry_name)
    return JsonResponse({"STATUS": "OK", "CODE": 0}, content_type="application/json")


@login_required
def export_members(request):
    """Export members to CSV"""
    from .exports import export_members_to_csv
    
    # Get filtered queryset
    members = Member.objects.all()
    
    # Apply same filters as list view
    community_filter = request.GET.get('community')
    if community_filter:
        members = members.filter(shepherd__name__icontains=community_filter)
    
    return export_members_to_csv(members)


@login_required
def import_members(request):
    """Import members from Excel file"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, _('Please select a file to upload.'))
            return redirect('list_members')
        
        file = request.FILES['file']
        
        # Check file extension
        if not file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, _('Please upload an Excel file (.xlsx or .xls).'))
            return redirect('list_members')
        
        try:
            import openpyxl
            from phonenumbers import parse, NumberParseException
            
            workbook = openpyxl.load_workbook(file)
            sheet = workbook.active
            
            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                headers.append(cell.value)
            
            # Expected headers based on Member model
            expected_headers = ['name', 'code', 'telephone', 'location', 'gender', 'shepherd', 'ministry', 'membership_category', 'pays_tithe', 'working', 'schooling']
            
            # Validate headers
            missing_headers = [h for h in expected_headers if h.lower() not in [str(h).lower() for h in headers]]
            if missing_headers:
                messages.error(request, _(f'Missing required columns: {", ".join(missing_headers)}'))
                return redirect('list_members')
            
            # Create header to column index mapping
            header_map = {str(h).lower(): idx for idx, h in enumerate(headers)}
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            # Start from row 2 (skip header)
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
                try:
                    # Extract data from row
                    name = row[header_map['name']].value
                    code = row[header_map['code']].value if 'code' in header_map else None
                    telephone = row[header_map['telephone']].value if 'telephone' in header_map else None
                    location = row[header_map['location']].value if 'location' in header_map else None
                    gender = row[header_map['gender']].value if 'gender' in header_map else None
                    shepherd_name = row[header_map['shepherd']].value if 'shepherd' in header_map else None
                    ministry_name = row[header_map['ministry']].value if 'ministry' in header_map else None
                    membership_category = row[header_map['membership_category']].value if 'membership_category' in header_map else None
                    pays_tithe = row[header_map['pays_tithe']].value if 'pays_tithe' in header_map else False
                    working = row[header_map['working']].value if 'working' in header_map else False
                    schooling = row[header_map['schooling']].value if 'schooling' in header_map else False
                    
                    # Validate required fields
                    if not name:
                        skipped_count += 1
                        continue
                    
                    # Check if member already exists
                    if Member.objects.filter(name=name).exists():
                        skipped_count += 1
                        continue
                    
                    # Get or create community
                    shepherd = None
                    if shepherd_name:
                        shepherd, created = Community.objects.get_or_create(
                            name=shepherd_name,
                            defaults={'location': 'Imported'}
                        )
                    
                    # Get or create ministry
                    ministry = None
                    if ministry_name:
                        ministry, created = Ministry.objects.get_or_create(
                            name=ministry_name
                        )
                    
                    # Normalize gender
                    if gender:
                        gender = str(gender).lower()
                        if gender not in ['male', 'female']:
                            gender = None
                    
                    # Normalize membership category
                    if membership_category:
                        membership_category = str(membership_category).lower()
                        if membership_category not in ['elder', 'youth', 'child']:
                            membership_category = None
                    
                    # Normalize boolean fields
                    pays_tithe = bool(pays_tithe) if pays_tithe else False
                    working = bool(working) if working else False
                    schooling = bool(schooling) if schooling else False
                    
                    # Create member
                    member = Member.objects.create(
                        name=name,
                        code=code,
                        telephone=str(telephone) if telephone else None,
                        location=location,
                        gender=gender,
                        shepherd=shepherd,
                        ministry=ministry,
                        membership_category=membership_category,
                        pays_tithe=pays_tithe,
                        working=working,
                        schooling=schooling,
                        active=True
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    skipped_count += 1
            
            if imported_count > 0:
                success_msg = _('Successfully imported %(count)s member(s).') % {'count': imported_count}
                if skipped_count > 0:
                    success_msg += f' {skipped_count} skipped.'
                if errors:
                    success_msg += f' Errors: {", ".join(errors[:5])}'
                messages.success(request, success_msg)
            else:
                messages.error(request, _('No members were imported. Please check your file format.'))
                if errors:
                    messages.error(request, ', '.join(errors[:3]))
            
            return redirect('list_members')
            
        except Exception as e:
            messages.error(request, _(f'Error processing file: {str(e)}'))
            return redirect('list_members')
    
    return render(request, 'members/import.html')