from django.urls import path
from .views import ( _login, login_user, _logout, signup, signup_user, user_profile, 
                    login_api,create_user, change_password,edit_user,view_user,list_users,delete_user,
                    # Family Views
                    FamilyListView, FamilyCreateView, FamilyDetailView, FamilyUpdateView, FamilyDeleteView,
                    # Family Membership Views
                    FamilyMembershipListView, FamilyMembershipCreateView, FamilyMembershipUpdateView, FamilyMembershipDeleteView,
                    # Priest Role Management Views
                    priest_role_management, assign_priest_role, remove_priest_role, priest_list)

urlpatterns = [
    # Login URLConfs
    path("login/", login_user, name="login_user"),
    path("_login_/", _login, name="_login"),
    path('logout/', _logout, name="_logout"),
    path('profile/', user_profile, name="role_management"),
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
    path('family-memberships/create/', FamilyMembershipCreateView.as_view(), name='family_membership_create'),
    path('family-memberships/<int:pk>/edit/', FamilyMembershipUpdateView.as_view(), name='family_membership_update'),
    path('family-memberships/<int:pk>/delete/', FamilyMembershipDeleteView.as_view(), name='family_membership_delete'),

    # Priest Role Management URLs
    path('priest-roles/', priest_role_management, name='priest_role_management'),
    path('priest-roles/list/', priest_list, name='priest_list'),
    path('priest-roles/<int:user_id>/assign/', assign_priest_role, name='assign_priest_role'),
    path('priest-roles/<int:user_id>/remove/', remove_priest_role, name='remove_priest_role'),
]