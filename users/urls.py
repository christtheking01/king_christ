from django.urls import path
from .views import ( _login, login_user, _logout, signup, signup_user, user_profile, 
                    login_api,create_user, change_password,edit_user,list_users,delete_user)

urlpatterns = [
    # Login URLConfs
    path("login/", login_user, name="login_user"),
    path("_login_/", _login, name="_login"),
    path('logout/', _logout, name="_logout"),
    path('profile/', user_profile, name="role_management"),
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
]