from django.urls import path
from .views import ( _login, login_user, _logout, signup, signup_user, user_profile, edit_profile,
                    login_api,create_user, change_password,edit_user,view_user,list_users,delete_user,
                    # Family Views
                    FamilyListView, FamilyCreateView, FamilyDetailView, FamilyUpdateView, FamilyDeleteView,
                    # Family Membership Views
                    FamilyMembershipListView, FamilyMembershipCreateView, FamilyMembershipUpdateView, FamilyMembershipDeleteView, FamilyBulkAddView, set_family_head,
                    # Priest Role Management Views
                    priest_role_management, assign_priest_role, remove_priest_role, priest_list,
                    # Sacrament Management Views
                    user_sacraments, add_user_sacrament, edit_user_sacrament, delete_user_sacrament,
                    # Portal Views
                    portal_register, portal_verify, portal_verify_session, portal_resend_code, portal_resend_code_session, portal_login, portal_logout,
                    portal_dashboard, portal_profile, portal_password_change, portal_events,
                    portal_event_detail, portal_tithe_history, portal_pledges, portal_community,
                    portal_ministry, portal_sacraments,
                    # Chart Views
                    TitheChartJSONView,
                    # Church Member Account Management Views
                    church_member_management, church_member_approve, church_member_block, church_member_delete,
                    church_member_bulk_approve, church_member_bulk_block, church_member_bulk_delete,
                    church_member_manual_link)

urlpatterns = [
    # Login URLConfs
    path("login/", login_user, name="login_user"),
    path("_login_/", _login, name="_login"),
    path('logout/', _logout, name="_logout"),
    path('profile/', user_profile, name="user_profile"),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/<int:user_id>/', view_user, name='view_user'),
    path('api/users/', create_user, name='add_user'),

    #profile url
    path('users/', list_users, name='list_users'),
    path('users/<int:user_id>/edit/', edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('change_password/', change_password, name='change_password'),


    # Api Login View Function
    path("login_api/", login_api, name="login_api"),

    # Signup URLConfs
    path("signup/", signup, name="signup"),
    path("signup_user/", signup_user, name="signup_user"),

    # Family URLs
    path('families/', FamilyListView.as_view(), name='family_list'),
    path('families/create/', FamilyCreateView.as_view(), name='family_create'),
    path('families/<int:pk>/', FamilyDetailView.as_view(), name='family_detail'),
    path('families/<int:pk>/edit/', FamilyUpdateView.as_view(), name='family_update'),
    path('families/<int:pk>/delete/', FamilyDeleteView.as_view(), name='family_delete'),

    # Family Membership URLs
    path('family-memberships/', FamilyMembershipListView.as_view(), name='family_membership_list'),
    path('family-memberships/bulk-add/', FamilyBulkAddView.as_view(), name='family_bulk_add'),
    path('family-memberships/create/', FamilyMembershipCreateView.as_view(), name='family_membership_create'),
    path('family-memberships/<int:pk>/edit/', FamilyMembershipUpdateView.as_view(), name='family_membership_update'),
    path('family-memberships/<int:pk>/delete/', FamilyMembershipDeleteView.as_view(), name='family_membership_delete'),
    path('family-memberships/<int:pk>/set-head/', set_family_head, name='set_family_head'),

    # Priest Role Management URLs
    path('priest-roles/', priest_role_management, name='priest_role_management'),
    path('priest-roles/list/', priest_list, name='priest_list'),
    path('priest-roles/<int:user_id>/assign/', assign_priest_role, name='assign_priest_role'),
    path('priest-roles/<int:user_id>/remove/', remove_priest_role, name='remove_priest_role'),

    # Sacrament Management URLs
    path('sacraments/', user_sacraments, name='user_sacraments'),
    path('sacraments/<int:user_id>/', user_sacraments, name='user_sacraments'),
    path('sacraments/<int:user_id>/add/', add_user_sacrament, name='add_user_sacrament'),
    path('sacraments/edit/<int:sacrament_id>/', edit_user_sacrament, name='edit_user_sacrament'),
    path('sacraments/delete/<int:sacrament_id>/', delete_user_sacrament, name='delete_user_sacrament'),

    # Member Portal URLs
    path('portal/', portal_dashboard, name='portal_dashboard'),
    path('portal/register/', portal_register, name='portal_register'),
    # Old verification (for existing users)
    path('portal/verify/<int:member_id>/', portal_verify, name='portal_verify'),
    path('portal/resend/<int:member_id>/', portal_resend_code, name='portal_resend_code'),
    # New session-based verification (user created AFTER verification)
    path('portal/verify/', portal_verify_session, name='portal_verify_session'),
    path('portal/resend/', portal_resend_code_session, name='portal_resend_code_session'),
    path('portal/login/', portal_login, name='portal_login'),
    path('portal/logout/', portal_logout, name='portal_logout'),
    path('portal/profile/', portal_profile, name='portal_profile'),
    path('portal/password/', portal_password_change, name='portal_password_change'),
    path('portal/events/', portal_events, name='portal_events'),
    path('portal/events/<int:event_id>/', portal_event_detail, name='portal_event_detail'),
    path('portal/tithes/', portal_tithe_history, name='portal_tithe_history'),
    path('portal/pledges/', portal_pledges, name='portal_pledges'),
    path('portal/community/', portal_community, name='portal_community'),
    path('portal/ministry/', portal_ministry, name='portal_ministry'),
    path('portal/sacraments/', portal_sacraments, name='portal_sacraments'),
    path('portal/chart/tithe-json/', TitheChartJSONView.as_view(), name='tithe_chart_json'),

    # Church Member Account Management URLs
    path('member-accounts/', church_member_management, name='church_member_management'),
    path('member-accounts/approve/<int:member_id>/', church_member_approve, name='church_member_approve'),
    path('member-accounts/block/<int:member_id>/', church_member_block, name='church_member_block'),
    path('member-accounts/delete/<int:member_id>/', church_member_delete, name='church_member_delete'),
    path('member-accounts/bulk-approve/', church_member_bulk_approve, name='church_member_bulk_approve'),
    path('member-accounts/bulk-block/', church_member_bulk_block, name='church_member_bulk_block'),
    path('member-accounts/bulk-delete/', church_member_bulk_delete, name='church_member_bulk_delete'),
    path('member-accounts/link/<int:member_id>/', church_member_manual_link, name='church_member_manual_link'),
]