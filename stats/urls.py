from django.urls import path
from . import views

from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'', views.RiotAccountViewSet)

urlpatterns = router.urls

urlpatterns += [
    # ex: /stats/
    path("", views.index, name="index"),
    # ex: /stats/calculate/
    path("calculate/", views.calculate, name="calculate"),
    path("import/", views.import_matches, name="import_matches"),
]



    # # ex: /stats/
    # path("", views.index, name="index"),
    # # ex: /stats/5/
    # path("<int:question_id>/", views.detail, name="detail"),
    # # ex: /stats/5/results/
    # path("<int:question_id>/results/", views.results, name="results"),
    # # ex: /stats/5/vote/
    # path("<int:question_id>/vote/", views.vote, name="vote"),