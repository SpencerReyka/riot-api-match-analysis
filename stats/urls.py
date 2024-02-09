from django.urls import path
from . import views

urlpatterns = [
    # ex: /stats/
    path("", views.index, name="index"),
    # ex: /stats/calculate/
    path("calculate/", views.calculate, name="calculate"),
]



    # # ex: /stats/
    # path("", views.index, name="index"),
    # # ex: /stats/5/
    # path("<int:question_id>/", views.detail, name="detail"),
    # # ex: /stats/5/results/
    # path("<int:question_id>/results/", views.results, name="results"),
    # # ex: /stats/5/vote/
    # path("<int:question_id>/vote/", views.vote, name="vote"),