from django.urls import path

from .views import (
    table_members, list_members, thumbnail_members, detail_member, edit_member, update_member, restore_member,
    delete_member, filter_members, search_members, get_members_by_statuses, get_members_by_shepherds, list_deleted_members,
    ministry_detail, ministry_list, create_ministry,update_ministry,list_committees,create_committee,
    list_shepherds, add_shepherd, create_shepherd,edit_community,delete_community, delete_ministry,
    edit_committee,delete_committee_member,CreateMembersView,AddMemberView
)

urlpatterns = [
    # UrlConf For Members
    path('list/', list_members, name="list_members"),
    path('table/', table_members, name="table_members"),
    path('thumbnail/', thumbnail_members, name="thumbnail_members"),
    path('detail/<int:pk>/', detail_member, name="detail_member"),
    path('edit/<int:pk>/', edit_member, name="edit_member"),
    path('update/<int:pk>/', update_member, name="update_member"),
    path('add/', AddMemberView.as_view(), name="add_member"),
    path('create/', CreateMembersView.as_view(), name="create_member"),
    path('delete/<int:pk>/', delete_member, name="delete_member"),
    path('filter/', filter_members, name="filter_members"),
    path('list/search/', search_members, name="search_members"),
    path('list/<status>/', get_members_by_statuses, name="get_members_by_statuses"),
    path('list_by_shepherd/<shepherd>/', get_members_by_shepherds, name="get_members_by_shepherd"),
    path('deleted/list/', list_deleted_members, name="list_deleted_members"),
    path('restore/<int:pk>/', restore_member, name="restore_members"),

    #urlConf fot committee
    path('committee/list/',list_committees,name="list_committees"),
    path('committee/create/',create_committee, name='create_committee'),
    path('committee/edit/<str:name>/',edit_committee, name='edit_committee'),
    path('committee/delete/<str:name>',delete_committee_member, name="delete_committee_member"),


    # UrlConf For Ministries
    path('ministries/list/', ministry_list, name='ministry_list'),
    path('ministry/create/', create_ministry, name='create_ministry'),
    path('ministry/<int:pk>/', ministry_detail, name='ministry_detail'),
    path('ministry/<int:pk>/update/', update_ministry, name='update_ministry'),
    path('ministry/<int:pk>/delete/', delete_ministry, name='delete_ministry'),

    # UrlConf For Communities
    path('shepherds/list/', list_shepherds, name="list_community"),
    path('shepherds/add/', add_shepherd, name="add_community"),
    path('shepherds/create/', create_shepherd, name="create_shepherd"),
    path('shepherds/edit/<int:community_id>/', edit_community, name="edit_community"),
    path('shepherds/delete/<int:community_id>/', delete_community, name="delete_community"),
    
]