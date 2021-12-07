
from django.http import HttpResponse, HttpRequest
from ..tests import PlatformAPITestCase
from ..models import ShareGroup, Datasource, Chart, User

def helloworld(request: HttpRequest) -> HttpResponse:
    return HttpResponse('Hello World')


def debug_reset_database(request: HttpRequest) -> HttpResponse:
    """DEBUG VIEW. DONT USE IN PRODUCTION! Clears the database and creates some entries for testing purposes.
    The data used is the same as used in the test cases
    """
    # Delete all users and groups
    for user in User.objects.all():
        user.delete()
    for group in ShareGroup.objects.all():
        group.delete()

    # Should have been done through cascadation, just to be safe
    # Delete all datasources and charts
    for datasource in Datasource.objects.all():
        datasource.delete()
    for chart in Chart.objects.all():
        chart.delete()

    # Setup database by creating a testcase object and using the setup call
    case = PlatformAPITestCase()
    case.client = case.client_class()
    case.SERVER_NAME = request.get_host().split(":")[0]
    case.SERVER_PORT = request.get_port()
    case.PROTO = 'https' if request.is_secure() else 'http'
    case.setup_demo()

    return HttpResponse('')