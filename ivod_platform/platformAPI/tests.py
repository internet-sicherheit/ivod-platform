from rest_framework.test import APITestCase
from django.shortcuts import reverse
from .permissions import *
from pathlib import Path
from shutil import rmtree
from .util import generate_chart, get_chart_base_path, get_datasource_base_path
from base64 import b64encode
from json import loads, load
from django.conf import settings
# Create your tests here.


class PlatformAPITestCase(APITestCase):

    def get_server_address(self):
        SERVER_NAME = getattr(self, 'SERVER_NAME', 'testserver')
        SERVER_PORT = getattr(self, 'SERVER_PORT', 80)
        return (SERVER_NAME,SERVER_PORT)

    def create_datasource(self, user, password, scope_path, data):
        data = {'data': f'{b64encode(data).decode(encoding="utf-8")}', 'scope_path': scope_path}
        url = reverse("datasource-add")
        self.assertTrue(self.client.login(username=user, password=password))
        (SERVER_NAME, SERVER_PORT) = self.get_server_address()
        response = self.client.post(url, data, format='json', SERVER_NAME=SERVER_NAME, SERVER_PORT=SERVER_PORT)
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        datasource = Datasource.objects.get(id=response.data['id'])
        self.assertIsNotNone(datasource)
        return datasource

    def create_chart(self, user, password, config, downloadable, visibility, scope_path, chart_name, datasource_id):
        data = {'config': config,
                'downloadable': downloadable,
                'visibility': visibility,
                'scope_path': scope_path,
                'chart_name': chart_name,
                'datasource': datasource_id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(username=user, password=password))
        (SERVER_NAME, SERVER_PORT) = self.get_server_address()
        response = self.client.post(url, data, format='json', SERVER_NAME=SERVER_NAME, SERVER_PORT=SERVER_PORT)
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        chart = Chart.objects.get(id=response.data['id'])
        self.assertIsNotNone(chart)
        return chart



    def setUp(self):
        #TODO: Actually generate datasources and charts with the API endpoints
        self.admin = User.objects.create_superuser(username="admin", email=None, password=getattr(settings, "ADMIN_PASS"))
        self.user1 = User.objects.create_user(username="user1", email=None, password="00000000")
        self.user2 = User.objects.create_user(username="user2", email=None, password="00000000")
        #Use user3 for a authenticated, but otherwise no permissions
        self.user3 = User.objects.create_user(username="user3", email=None, password="00000000")
        self.user4 = User.objects.create_user(username="user4", email=None, password="00000000")

        self.group1 = Group.objects.create(name="group1")
        self.group2 = Group.objects.create(name="group2")
        self.group1.user_set.add(self.user4)

        datasource_output_path = get_datasource_base_path()
        if datasource_output_path.exists():
            rmtree(path=datasource_output_path)
        datasource_output_path.mkdir(exist_ok=True, parents=True)

        datasource_base_path = Path(__file__).resolve().parent.joinpath("sample-data").joinpath("data").joinpath("metadata")
        with datasource_base_path.joinpath("simple_series.json").open("rb") as source_file:
            self.datasource1 = self.create_datasource(self.user1.username, "00000000", "/file1", source_file.read())
        with datasource_base_path.joinpath("numerical.json").open("rb") as source_file:
            self.datasource2 = self.create_datasource(self.user2.username, "00000000", "/file2", source_file.read())

        base_path = get_chart_base_path()
        if base_path.exists():
            rmtree(path=base_path)
        base_path.mkdir(exist_ok=True, parents=True)

        self.chart1 = self.create_chart(self.user1.username, "00000000", "{}", True, Chart.VISIBILITY_PRIVATE, "/piechart1", "piechart", self.datasource1.id)

        self.chart2 = self.create_chart(self.user1.username, "00000000", "{}", False, Chart.VISIBILITY_SHARED,
                                        "/piechart2", "piechart", self.datasource1.id)
        self.chart3 = self.create_chart(self.user2.username, "00000000", "{}", False, Chart.VISIBILITY_PRIVATE,
                                        "/linechart1", "linechart", self.datasource2.id)
        self.chart4 = self.create_chart(self.user2.username, "00000000", "{}", True, Chart.VISIBILITY_PRIVATE,
                                        "/linechart2", "linechart", self.datasource2.id)
        self.chart5 = self.create_chart(self.user2.username, "00000000", "{}", True, Chart.VISIBILITY_PUBLIC,
                                        "/linechart3", "linechart", self.datasource2.id)

        self.chart2.shared_users.add(self.user2)
        self.chart2.shared_groups.add(self.group1)
        self.chart2.save()
        self.datasource1.shared_users.add(self.user2)
        self.datasource1.shared_groups.add(self.group1)
        self.datasource1.save()

    def test_datasources_list_unautenticated(self):
        # Access listing of datasources unauthenticated -> Error 403
        data = {}
        url = reverse("datasource-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_list_unautenticated(self):
        # Access listing of charts unauthenticated -> Error 403
        data = {}
        url = reverse("chart-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_list_authenticated(self):
        # Access listing of datasources authenticated, but with none owned or shared -> Success, but empty response
        data = {}
        url = reverse("datasource-add")
        self.client.login(username='user3', password='00000000')
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response_obj = response.data
        self.assertEquals(len(response_obj), 0)

    def test_chart_list_authenticated_public_only(self):
        # Access listing of charts authenticated, but with none owned or shared directly -> Success, but show only public charts
        data = {}
        url = reverse("chart-add")
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        #There is 1 public chart in the database
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["scope_path"], "/linechart3")

    def test_chart_read_not_shared_not_owned(self):
        # Access a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_read_shared_to_user(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/piechart2")

    def test_chart_read_shared_to_group(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/piechart2")

    def test_chart_read_owned(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/piechart2")

    def test_chart_data_read_not_shared_not_owned(self):
        # Access a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_data_read_shared_to_user(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        with get_chart_base_path().joinpath(str(self.chart2.id)).joinpath('data.json').open('r') as data_file:
            self.assertEquals(loads(response.content.decode('utf-8')), load(data_file))
        self.assertNotEqual(response.content.decode('utf-8'), "")
        self.assertNotEqual(response.content.decode('utf-8'), "{}")

    def test_chart_data_read_shared_to_group(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        with get_chart_base_path().joinpath(str(self.chart2.id)).joinpath('data.json').open('r') as data_file:
            self.assertEquals(loads(response.content.decode('utf-8')), load(data_file))
        self.assertNotEqual(response.content.decode('utf-8'), "")
        self.assertNotEqual(response.content.decode('utf-8'), "{}")

    def test_chart_data_read_owned(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        with get_chart_base_path().joinpath(str(self.chart2.id)).joinpath('data.json').open('r') as data_file:
            self.assertEquals(loads(response.content.decode('utf-8')), load(data_file))
        self.assertNotEqual(response.content.decode('utf-8'), "")
        self.assertNotEqual(response.content.decode('utf-8'), "{}")

    def test_datasource_read_not_shared_not_owned(self):
        # Access a datasource directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_read_shared_to_user(self):
        # Access a datasource directly by its key, with it being shared -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/file1")

    def test_datasource_read_shared_to_group(self):
        # Access a datasource directly by its key, with it being shared -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/file1")

    def test_datasource_read_owned(self):
        # Access a datasource directly by its key, with it being owned -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/file1")

    def test_datasource_edit_owned(self):
        # Change scope path on an owned datasource -> 200, scope path changed
        data = { 'scope_path': '/test/datasource/edit/owned'}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], '/test/datasource/edit/owned')

    def test_datasource_edit_owned_no_change(self):
        # Dont change scope path on an owned datasource -> 200, scope path unchanged
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], self.datasource1.scope_path)

    def test_datasource_edit_owned_unsupported_change(self):
        # Change not existing field on an owned datasource -> 200, field is ignored
        data = { 'NOT_ACTUALLY_A_FIELD' : 'NOT_ACTUALLY_DATA'}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_chart_delete_authenticated_public_only(self):
        # Delete a chart directly by its key, with it being public -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_user(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_group(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        # Delete a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)

    def test_datasource_delete_authenticated_only(self):
        # Delete a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_user(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_group(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        # Delete a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_chart_edit_authenticated_public_only(self):
        # Modify public chart in a legal way -> Error 403
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_shared_to_user(self):
        # Modify shared chart in a legal way -> Error 403
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_shared_to_group(self):
        # Modify shared chart in a legal way -> Error 403
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_owned(self):
        # Modify owned chart in a legal way -> Success
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data = {'scope_path': '/new/scope'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['scope_path'], '/new/scope')

        data = {'config': '{\"info\": \"new config\"}'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['config'], '{\"info\": \"new config\"}')

        data = {'downloadable': False}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['downloadable'], False)

        data = {'visibility': Chart.VISIBILITY_PUBLIC}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['visibility'], Chart.VISIBILITY_PUBLIC)

        # Modify owned chart in an illegal way -> Success, but no actual modification takes place
        data = {'chart_name': 'SHOULD BE READ ONLY'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertNotEqual(response.data['chart_name'], 'SHOULD BE READ ONLY')

    def test_create_datasource(self):
        # Create a new datasource -> Datasource in Database
        data = {'url': 'https://google.com', 'scope_path': '/test/create/datasource'}
        url = reverse("datasource-add")
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)
        datasource = Datasource.objects.get(id=response.data['id'])
        self.assertIsNotNone(datasource)

    def test_create_chart(self):
        # Create a new chart with a datasource user has access too -> Chart in Database
        data = {'config': '{}',
                'downloadable': True,
                'visibility': Chart.VISIBILITY_PRIVATE,
                'scope_path': '/test/create/chart',
                'chart_name': 'barchart',
                'datasource': self.datasource1.id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)
        chart = Chart.objects.get(id=response.data['id'])
        self.assertIsNotNone(chart)

    def test_create_chart_with_unaccessible_datasource(self):
        # Create a new chart with a datasource user DOES NOT have access too -> Error 403
        data = {'config': '{}',
                'downloadable': True,
                'visibility': Chart.VISIBILITY_PRIVATE,
                'scope_path': '/test/create/chart',
                'chart_name': 'TESTNAME',
                'datasource': self.datasource2.id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_as_owner(self):
        # As the owner, share a chart with another user -> 200, new user is added
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['users'], [self.user2.id])

        response = self.client.patch(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['users']), 2)
        self.assertTrue(self.user2.id in data_after['users'])
        self.assertTrue(self.user3.id in data_after['users'])
        self.assertEquals(set(data_after['groups']), set(data_before.data['groups']))


    def test_add_user_to_share_as_shared_to_user(self):
        # As someone with the chart shared, share a chart with another user -> 403
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_as_shared_to_group(self):
        # As someone with the chart shared, share a chart with another user -> 403
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_authenticated_only(self):
        # As someone with the chart NOT shared, share a chart with another user -> 403
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_user_from_share_as_owner(self):
        # As the owner, unshare a chart with another user -> 200, user is not in shares anymore
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['users'], [self.user2.id])

        response = self.client.delete(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['users']), 0)
        self.assertEquals(set(data_after['groups']), set(data_before.data['groups']))


    def test_del_shared_from_share_as_shared_to_user(self):
        # As someone with the chart shared, unshare a chart with another user -> 403
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_from_share_as_shared_to_group(self):
        # As someone with the chart shared, unshare a chart with another user -> 403
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_from_share_authenticated_only(self):
        # As someone with the chart NOT shared, unshare a chart with another user -> 403
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_not_shared_user_from_share_as_owner(self):
        # Unshare a chart that wasnt actually shared -> 200, chart still not shared with user
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['users'], [self.user2.id])

        response = self.client.delete(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['users']), 1)
        self.assertEquals(data_before.data['users'], [self.user2.id])
        self.assertEquals(set(data_after['groups']), set(data_before.data['groups']))

    def test_share_with_already_shared_user_from_share_as_owner(self):
        # Share a chart that was already shared -> 200, chart shared with user
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['users'], [self.user2.id])

        response = self.client.patch(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['users']), 1)
        self.assertEquals(data_before.data['users'], [self.user2.id])
        self.assertEquals(set(data_after['groups']), set(data_before.data['groups']))

    def test_chart_access_after_share(self):
        # Share a chart, check if permissions changed
        data = {'users': [self.user3.id]}
        share_url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        access_url = reverse("chart-get", kwargs={'pk': self.chart2.id})

        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(access_url, format='json')
        self.assertEquals(response.status_code, 403)

        self.client.logout()
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.patch(share_url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.client.logout()

        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(access_url, format='json')
        self.assertEquals(response.status_code, 200)


    def test_add_group_to_share_as_owner(self):
        # As the owner, share a chart with another user -> 200, new user is added
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['groups'], [self.group1.id])

        response = self.client.patch(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['groups']), 2)
        self.assertTrue(self.group1.id in data_after['groups'])
        self.assertTrue(self.group2.id in data_after['groups'])
        self.assertEquals(set(data_after['users']), set(data_before.data['users']))


    def test_add_group_to_share_as_shared_to_user(self):
        # As someone with the chart shared, share a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_group_to_share_as_shared_to_group(self):
        # As someone with the chart shared, share a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_group_to_share_authenticated_only(self):
        # As someone with the chart NOT shared, share a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_as_owner(self):
        # As the owner, unshare a chart with another group -> 200, group is not in shares anymore
        data = {'groups': [self.group1.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['groups'], [self.group1.id])

        response = self.client.delete(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['groups']), 0)
        self.assertEquals(set(data_after['users']), set(data_before.data['users']))


    def test_del_shared_group_from_share_as_shared_to_user(self):
        # As someone with the chart shared, unshare a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_as_shared_to_group(self):
        # As someone with the chart shared, unshare a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user4', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_authenticated_only(self):
        # As someone with the chart NOT shared, unshare a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_not_shared_group_user_from_share_as_owner(self):
        # Unshare a chart that wasnt actually shared -> 200, chart still not shared with user
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['groups'], [self.group1.id])

        response = self.client.delete(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['groups']), 1)
        self.assertEquals(data_before.data['groups'], [self.group1.id])
        self.assertEquals(set(data_after['users']), set(data_before.data['users']))

    def test_share_with_already_shared_group_from_share_as_owner(self):
        # Share a chart that was already shared -> 200, chart shared with group
        data = {'groups': [self.group1.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['groups'], [self.group1.id])

        response = self.client.patch(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['groups']), 1)
        self.assertEquals(data_before.data['groups'], [self.group1.id])
        self.assertEquals(set(data_after['users']), set(data_before.data['users']))

    #TODO: Check responses for values that should not be visible for all users to confirm correct filtering on serializer level