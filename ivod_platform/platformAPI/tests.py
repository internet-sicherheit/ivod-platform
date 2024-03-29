import json

from rest_framework.test import APITestCase
from django.shortcuts import reverse
from .models import Datasource, Chart, ShareGroup, ShareableModel
from .models import User
from pathlib import Path
from shutil import rmtree
from .util import generate_chart, get_chart_base_path, get_datasource_base_path, get_code_base_path, get_config_for_chart
from base64 import b64encode
from json import loads, load
from django.conf import settings

class PlatformAPITestCase(APITestCase):

    def get_server_address(self):
        SERVER_NAME = getattr(self, 'SERVER_NAME', 'testserver')
        SERVER_PORT = getattr(self, 'SERVER_PORT', 80)
        PROTO = getattr(self, 'PROTO', 'http')
        return (SERVER_NAME,SERVER_PORT, PROTO)

    def create_datasource(self, user, password, datasource_name, data, visibility=ShareableModel.VISIBILITY_PRIVATE):
        data = {'data': f'{b64encode(data).decode(encoding="utf-8")}', 'datasource_name': datasource_name, 'visibility':visibility}
        url = reverse("datasource-add")
        self.assertTrue(self.client.login(email=user, password=password))
        (SERVER_NAME, SERVER_PORT,PROTO) = self.get_server_address()
        response = self.client.post(url, data, format='json',  **{"SERVER_NAME": SERVER_NAME, "SERVER_PORT": SERVER_PORT, "wsgi.url_scheme": PROTO})
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        datasource = Datasource.objects.get(id=response.data['id'])
        self.assertIsNotNone(datasource)
        return datasource

    def create_chart(self, user, password, config, downloadable, visibility, chart_name, chart_type, datasource_id):
        data = {'config': config,
                'downloadable': downloadable,
                'visibility': visibility,
                'chart_name': chart_name,
                'chart_type': chart_type,
                'datasource': datasource_id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(email=user, password=password))
        (SERVER_NAME, SERVER_PORT, PROTO) = self.get_server_address()
        response = self.client.post(url, data, format='json', **{"SERVER_NAME": SERVER_NAME, "SERVER_PORT": SERVER_PORT, "wsgi.url_scheme": PROTO})
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        chart = Chart.objects.get(id=response.data['id'])
        self.assertIsNotNone(chart)
        return chart

    def create_group(self, user, password, name, public=False, admins=[], members=[]):
        data = {'name': name,
                'is_public': public,
                'group_admins': admins,
                'group_members': members
                }
        url = reverse("sharegroup-add")
        self.assertTrue(self.client.login(email=user, password=password))
        (SERVER_NAME, SERVER_PORT, PROTO) = self.get_server_address()
        response = self.client.post(url, data, format='json', **{"SERVER_NAME": SERVER_NAME, "SERVER_PORT": SERVER_PORT,
                                                                 "wsgi.url_scheme": PROTO})
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        group = ShareGroup.objects.get(id=response.data['id'])
        self.assertIsNotNone(group)
        return group

    def setUp(self):
        #TODO: Actually generate datasources and charts with the API endpoints
        self.admin = User.objects.create_superuser(email="admin@localhost", username="admin", password=getattr(settings, "ADMIN_PASS"))
        self.user1 = User.objects.create_user(email="user1@localhost", username="user1", password="00000000", is_verified=True)
        self.user2 = User.objects.create_user(email="user2@localhost", username="user2", password="00000000", is_verified=True)
        #Use user3 for a authenticated, but otherwise no permissions
        self.user3 = User.objects.create_user(email="user3@localhost", username="user3", password="00000000", is_verified=True)
        self.user4 = User.objects.create_user(email="user4@localhost", username="user4", password="00000000", is_verified=True)


        self.group1 = self.create_group("user1@localhost", "00000000", "group1", public=False, admins=[self.user2.id], members=[self.user4.id])
        self.group2 = self.create_group("user1@localhost", "00000000", "group2", public=False, admins=[], members=[])

        datasource_output_path = get_datasource_base_path()
        if datasource_output_path.exists():
            rmtree(path=datasource_output_path)
        datasource_output_path.mkdir(exist_ok=True, parents=True)

        datasource_base_path = Path(__file__).resolve().parent.joinpath("sample-data").joinpath("data").joinpath("metadata")
        with datasource_base_path.joinpath("simple_series.json").open("rb") as source_file:
            self.datasource1 = self.create_datasource(self.user1.email, "00000000", "/file1", source_file.read(), ShareableModel.VISIBILITY_SHARED)
        with datasource_base_path.joinpath("numerical.json").open("rb") as source_file:
            self.datasource2 = self.create_datasource(self.user2.email, "00000000", "/file2", source_file.read())

        base_path = get_chart_base_path()
        if base_path.exists():
            rmtree(path=base_path)
        base_path.mkdir(exist_ok=True, parents=True)

        self.chart1 = self.create_chart(self.user1.email, "00000000", "{}", True, Chart.VISIBILITY_PRIVATE, "/piechart1", "piechart", self.datasource1.id)

        self.chart2 = self.create_chart(self.user1.email, "00000000", "{}", False, Chart.VISIBILITY_SHARED,
                                        "/piechart2", "piechart", self.datasource1.id)
        self.chart3 = self.create_chart(self.user2.email, "00000000", "{}", False, Chart.VISIBILITY_PRIVATE,
                                        "/linechart1", "linechart", self.datasource2.id)
        self.chart4 = self.create_chart(self.user2.email, "00000000", "{}", True, Chart.VISIBILITY_PRIVATE,
                                        "/linechart2", "linechart", self.datasource2.id)
        self.chart5 = self.create_chart(self.user2.email, "00000000", "{}", True, Chart.VISIBILITY_PUBLIC,
                                        "/linechart3", "linechart", self.datasource2.id)

        self.chart2.shared_users.add(self.user2)
        self.chart2.shared_groups.add(self.group1)
        self.chart2.save()
        self.datasource1.shared_users.add(self.user2)
        self.datasource1.shared_groups.add(self.group1)
        self.datasource1.save()

        self.valid_dashboard_config = json.dumps({
    'horizontal': False,
    'aspect': [900, 600],
    'c1': {
      'split': {
        'horizontal': True,
        'aspect': [200, 100],
        'c1': {
          'split': {
            'horizontal': False,
            'aspect': [100, 50],
            'c1': {
              'generatorName': "chart",
              'args': {'chartID': 32}
            },
            'c2': {
              'generatorName': "chart",
              'args': {'chartID': 32}
            },
          }
        },
        'c2': {
          'split': {
            'horizontal': False,
            'DEBUG': 2,
            'aspect': [100, 50],
            'c1': {
              'generatorName': "chart",
              'args': {'chartID': 32}
            },
            'c2': {
              'generatorName': "chart",
              'args': {'chartID': 32}
            },
          }
        }
      }
    }
  })
        self.invalid_dashboard_config1 = ""
        self.invalid_dashboard_config2 = "A dictionary is expected, not a string."

    def test_datasources_list_unautenticated(self):
        # Access listing of datasources unauthenticated -> Error 403
        data = {}
        url = reverse("datasource-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_list_unautenticated(self):
        # Access listing of charts unauthenticated -> Return all charts with Public Permission
        data = {}
        url = reverse("chart-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 200)
        # There is 1 public chart in the database
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["chart_name"], "/linechart3")

    def test_datasource_list_authenticated(self):
        # Access listing of datasources authenticated, but with none owned or shared -> Success, but empty response
        data = {}
        url = reverse("datasource-add")
        self.client.login(email='user3@localhost', password='00000000')
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response_obj = response.data
        self.assertEquals(len(response_obj), 0)

    def test_chart_list_authenticated_public_only(self):
        # Access listing of charts authenticated, but with none owned or shared directly -> Success, but show only public charts
        data = {}
        url = reverse("chart-add")
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        #There is 1 public chart in the database
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["chart_name"], "/linechart3")

    def test_chart_read_not_shared_not_owned(self):
        # Access a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart1.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_read_shared_to_user(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["chart_name"], "/piechart2")

    def test_chart_read_shared_to_group(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["chart_name"], "/piechart2")

    def test_chart_read_owned(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["chart_name"], "/piechart2")

    def test_chart_data_read_not_shared_not_owned(self):
        # Access a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_data_read_shared_to_user(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-data", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
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
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
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
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        with get_chart_base_path().joinpath(str(self.chart2.id)).joinpath('data.json').open('r') as data_file:
            self.assertEquals(loads(response.content.decode('utf-8')), load(data_file))
        self.assertNotEqual(response.content.decode('utf-8'), "")
        self.assertNotEqual(response.content.decode('utf-8'), "{}")

    def test_chart_code_read(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-code", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json', follow=True)
        self.assertEquals(response.status_code, 200)

        config = get_config_for_chart(self.chart2)
        version = config['version']
        with get_chart_base_path().joinpath(str(self.chart2.id)).joinpath('persisted.json').open('r') as file:
            config = load(file)
            name = config['chart_name'].lower() + ".js"
        with get_code_base_path().joinpath(version).joinpath(name).open('rb') as code_file:
            self.assertEquals(b''.join(response.streaming_content), code_file.read())

    def test_chart_config_read(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-config", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json', follow=True)
        self.assertEquals(response.status_code, 200)

        config = get_config_for_chart(self.chart2)
        self.assertEquals(loads(response.content), config)

    def test_chart_file_read_whitelisted(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-files", kwargs={'pk': self.chart2.id, 'filename': 'config.json'})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json', follow=True)
        self.assertEquals(response.status_code, 200)

        config = get_config_for_chart(self.chart2)
        self.assertEquals(loads(response.content), config)

    def test_chart_file_read_not_whitelisted(self):
        # Access a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-files", kwargs={'pk': self.chart2.id, 'filename': 'persisted.json'})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json', follow=True)
        self.assertEquals(response.status_code, 404)


    def test_datasource_read_not_shared_not_owned(self):
        # Access a datasource directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_read_shared_to_user(self):
        # Access a datasource directly by its key, with it being shared -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["datasource_name"], "/file1")

    def test_datasource_read_shared_to_group(self):
        # Access a datasource directly by its key, with it being shared -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["datasource_name"], "/file1")

    def test_datasource_read_owned(self):
        # Access a datasource directly by its key, with it being owned -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["datasource_name"], "/file1")

    def test_datasource_edit_owned(self):
        # Change scope path on an owned datasource -> 200, scope path changed
        data = { 'datasource_name': '/test/datasource/edit/owned'}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["datasource_name"], '/test/datasource/edit/owned')

    def test_datasource_edit_owned_no_change(self):
        # Dont change scope path on an owned datasource -> 200, scope path unchanged
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["datasource_name"], self.datasource1.datasource_name)

    def test_datasource_edit_owned_unsupported_change(self):
        # Change not existing field on an owned datasource -> 200, field is ignored
        data = { 'NOT_ACTUALLY_A_FIELD' : 'NOT_ACTUALLY_DATA'}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_chart_delete_authenticated_public_only(self):
        # Delete a chart directly by its key, with it being public -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_user(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_group(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        # Delete a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)

    def test_datasource_delete_authenticated_only(self):
        # Delete a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_user(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared_to_group(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        # Delete a chart directly by its key, with it being owned -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_chart_edit_authenticated_public_only(self):
        # Modify public chart in a legal way -> Error 403
        data = {'chart_name': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_shared_to_user(self):
        # Modify shared chart in a legal way -> Error 403
        data = {'chart_name': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_shared_to_group(self):
        # Modify shared chart in a legal way -> Error 403
        data = {'chart_name': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_owned(self):
        # Modify owned chart in a legal way -> Success
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

        data = {'chart_name': '/new/scope'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['chart_name'], '/new/scope')

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
        data = {'chart_type': 'SHOULD BE READ ONLY'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertNotEqual(response.data['chart_type'], 'SHOULD BE READ ONLY')

    def test_create_datasource(self):
        # Create a new datasource -> Datasource in Database
        data = {'url': 'https://google.com', 'datasource_name': '/test/create/datasource'}
        url = reverse("datasource-add")
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)
        datasource = Datasource.objects.get(id=response.data['id'])
        self.assertIsNotNone(datasource)

    def test_create_chart(self):
        # Create a new chart with a datasource user has access too -> Chart in Database
        data = {'config': '{}',
                'downloadable': True,
                'visibility': Chart.VISIBILITY_PRIVATE,
                'chart_name': '/test/create/chart',
                'chart_type': 'barchart',
                'datasource': self.datasource1.id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)
        chart = Chart.objects.get(id=response.data['id'])
        self.assertIsNotNone(chart)

    def test_create_chart_with_illegal_chart_type(self):
        # Create a new chart with a datasource user has access too -> Chart in Database
        data = {'config': '{}',
                'downloadable': True,
                'visibility': Chart.VISIBILITY_PRIVATE,
                'chart_name': '/test/create/chart',
                'chart_type': 'ILLEGAL',
                'datasource': self.datasource1.id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 400)

    # TODO: Make sure no chart artifacts remain on midway crash, but how to force midway crash?

    def test_create_chart_with_unaccessible_datasource(self):
        # Create a new chart with a datasource user DOES NOT have access too -> Error 403
        data = {'config': '{}',
                'downloadable': True,
                'visibility': Chart.VISIBILITY_PRIVATE,
                'chart_name': '/test/create/chart',
                'chart_type': 'TESTNAME',
                'datasource': self.datasource2.id
                }
        url = reverse("chart-add")
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_as_owner(self):
        # As the owner, share a chart with another user -> 200, new user is added
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_as_shared_to_group(self):
        # As someone with the chart shared, share a chart with another user -> 403
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_authenticated_only(self):
        # As someone with the chart NOT shared, share a chart with another user -> 403
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_user_from_share_as_owner(self):
        # As the owner, unshare a chart with another user -> 200, user is not in shares anymore
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_from_share_as_shared_to_group(self):
        # As someone with the chart shared, unshare a chart with another user -> 403
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_from_share_authenticated_only(self):
        # As someone with the chart NOT shared, unshare a chart with another user -> 403
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_not_shared_user_from_share_as_owner(self):
        # Unshare a chart that wasnt actually shared -> 200, chart still not shared with user
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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

        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(access_url, format='json')
        self.assertEquals(response.status_code, 403)

        self.client.logout()
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))
        response = self.client.patch(share_url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.client.logout()

        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))
        response = self.client.get(access_url, format='json')
        self.assertEquals(response.status_code, 200)

    def test_add_group_to_share_as_owner(self):
        # As the owner, share a chart with another user -> 200, new user is added
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_group_to_share_as_shared_to_group(self):
        # As someone with the chart shared, share a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_group_to_share_authenticated_only(self):
        # As someone with the chart NOT shared, share a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_as_owner(self):
        # As the owner, unshare a chart with another group -> 200, group is not in shares anymore
        data = {'groups': [self.group1.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user2@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_as_shared_to_group(self):
        # As someone with the chart shared, unshare a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_group_from_share_authenticated_only(self):
        # As someone with the chart NOT shared, unshare a chart with another group -> 403
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user3@localhost', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_not_shared_group_user_from_share_as_owner(self):
        # Unshare a chart that wasnt actually shared -> 200, chart still not shared with user
        data = {'groups': [self.group2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

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
        self.assertTrue(self.client.login(email='user1@localhost', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['groups'], [self.group1.id])

        response = self.client.patch(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['groups']), 1)
        self.assertEquals(data_before.data['groups'], [self.group1.id])
        self.assertEquals(set(data_after['users']), set(data_before.data['users']))

    def test_create_new_group_unautenticated(self):
        data = {'name': 'test_create_new_group_unautenticated',
                'is_public': True
                }
        url = reverse("sharegroup-add")
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_create_new_group_with_members(self):
        data = {'name': 'test_create_new_group_with_members',
                'is_public': True,
                'group_admins': [self.user1.id, self.user2.id, self.user4.id],
                'group_members': [self.user1.id, self.user2.id, self.user3.id]
                }
        url = reverse("sharegroup-add")
        self.assertTrue(self.client.login(email=self.user1.email, password="00000000"))
        response = self.client.post(url, data, format='json')
        self.client.logout()
        self.assertEquals(response.status_code, 201)
        group = ShareGroup.objects.get(id=response.data['id'])
        self.assertIsNotNone(group)
        self.assertEquals(group.owner, self.user1)
        self.assertIn(self.user1, group.group_admins.all())
        self.assertIn(self.user2, group.group_admins.all())
        self.assertIn(self.user4, group.group_admins.all())
        self.assertIn(self.user1, group.group_members.all())
        self.assertIn(self.user2, group.group_members.all())
        self.assertIn(self.user3, group.group_members.all())

    def test_delete_group_member_as_owner(self):
        data = {'name': 'test_delete_group_member_as_owner',
                'is_public': True,
                'group_admins': [self.user1.id, self.user2.id, self.user4.id],
                'group_members': [self.user1.id, self.user2.id, self.user3.id]
                }
        url = reverse("sharegroup-add")
        self.assertTrue(self.client.login(email=self.user1.email, password="00000000"))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)

        data = {
            'group_members': [self.user2.id]
        }
        url = reverse("sharegroup-properties", kwargs={'pk': response.data['id']})
        after = self.client.delete(url, data, format='json')
        group = ShareGroup.objects.get(id=response.data['id'])
        self.assertIsNotNone(group)
        self.assertEquals(group.owner, self.user1)
        self.assertIn(self.user1, group.group_admins.all())
        self.assertIn(self.user2, group.group_admins.all())
        self.assertIn(self.user4, group.group_admins.all())
        self.assertIn(self.user1, group.group_members.all())
        self.assertNotIn(self.user2, group.group_members.all())
        self.assertIn(self.user3, group.group_members.all())

    def test_delete_group_member_as_admin(self):
        data = {'name': 'test_delete_group_member_as_owner',
                'is_public': True,
                'group_admins': [self.user1.id, self.user2.id, self.user4.id],
                'group_members': [self.user1.id, self.user2.id, self.user3.id]
                }
        url = reverse("sharegroup-add")
        self.assertTrue(self.client.login(email=self.user4.email, password="00000000"))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)

        data = {
            'group_members': [self.user2.id]
        }
        url = reverse("sharegroup-properties", kwargs={'pk': response.data['id']})
        after = self.client.delete(url, data, format='json')
        group = ShareGroup.objects.get(id=response.data['id'])
        self.assertIsNotNone(group)
        self.assertEquals(group.owner, self.user4)
        self.assertIn(self.user1, group.group_admins.all())
        self.assertIn(self.user2, group.group_admins.all())
        self.assertIn(self.user4, group.group_admins.all())
        self.assertIn(self.user1, group.group_members.all())
        self.assertNotIn(self.user2, group.group_members.all())
        self.assertIn(self.user3, group.group_members.all())

    def test_delete_group_member_as_member(self):
        data = {'name': 'test_delete_group_member_as_owner',
                'is_public': True,
                'group_admins': [self.user1.id, self.user2.id, self.user4.id],
                'group_members': [self.user1.id, self.user2.id, self.user3.id]
                }
        url = reverse("sharegroup-add")
        self.assertTrue(self.client.login(email=self.user1.email, password="00000000"))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)

        data = {
            'group_members': [self.user2.id]
        }
        url = reverse("sharegroup-properties", kwargs={'pk': response.data['id']})
        self.assertTrue(self.client.login(email=self.user3.email, password="00000000"))
        after = self.client.delete(url, data, format='json')
        self.assertEquals(after.status_code, 403)
        group = ShareGroup.objects.get(id=response.data['id'])
        self.assertIsNotNone(group)
        self.assertEquals(group.owner, self.user1)
        self.assertIn(self.user1, group.group_admins.all())
        self.assertIn(self.user2, group.group_admins.all())
        self.assertIn(self.user4, group.group_admins.all())
        self.assertIn(self.user1, group.group_members.all())
        self.assertIn(self.user2, group.group_members.all())
        self.assertIn(self.user3, group.group_members.all())

    def add_user_to_group(self, inserting_user, inserted_users, group, member=True, admin=False):
        data = {}
        if member:
            data['group_members'] = [user.id for user in inserted_users]
        if admin:
            data['group_admins'] = [user.id for user in inserted_users]
        url = reverse("sharegroup-properties", kwargs={'pk': group.id})
        if inserting_user:
            self.assertTrue(self.client.login(email=inserting_user.email, password='00000000'))
        before_state = self.client.get(url, format='json')
        after_state = self.client.patch(url, data, format='json')
        if inserting_user:
            self.client.logout()
        return (before_state, after_state)

    def test_add_user_to_group_members_as_owner(self):
        before_state, after_state = self.add_user_to_group(self.user1, [self.user3], self.group1, True, False)

        self.assertNotIn(self.user3.id, before_state.data['group_members'])
        self.assertNotIn(self.user3.id, before_state.data['group_admins'])
        self.assertEquals(after_state.status_code, 200)
        self.assertIn(self.user3.id, after_state.data['group_members'])
        self.assertNotIn(self.user3.id, after_state.data['group_admins'])

    def test_add_user_to_group_admins_as_owner(self):
        before_state, after_state = self.add_user_to_group(self.user1, [self.user3], self.group1, False, True)

        self.assertNotIn(self.user3.id, before_state.data['group_members'])
        self.assertNotIn(self.user3.id, before_state.data['group_admins'])
        self.assertEquals(after_state.status_code, 200)
        self.assertNotIn(self.user3.id, after_state.data['group_members'])
        self.assertIn(self.user3.id, after_state.data['group_admins'])

    def test_add_user_to_group_members_as_admin(self):
        before_state, after_state = self.add_user_to_group(self.user2, [self.user3], self.group1, True, False)

        self.assertNotIn(self.user3.id, before_state.data['group_members'])
        self.assertNotIn(self.user3.id, before_state.data['group_admins'])
        self.assertEquals(after_state.status_code, 200)
        self.assertIn(self.user3.id, after_state.data['group_members'])
        self.assertNotIn(self.user3.id, after_state.data['group_admins'])

    def test_add_user_to_group_admins_as_admin(self):
        before_state, after_state = self.add_user_to_group(self.user2, [self.user3], self.group1, False, True)

        self.assertNotIn(self.user3.id, before_state.data['group_members'])
        self.assertNotIn(self.user3.id, before_state.data['group_admins'])
        self.assertEquals(after_state.status_code, 200)
        self.assertNotIn(self.user3.id, after_state.data['group_members'])
        self.assertIn(self.user3.id, after_state.data['group_admins'])

    def test_add_user_to_group_members_as_member(self):
        before_state, after_state = self.add_user_to_group(self.user4, [self.user3], self.group1, True, False)

        self.assertEquals(before_state.status_code, 403)
        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_add_user_to_group_admins_as_member(self):
        before_state, after_state = self.add_user_to_group(self.user4, [self.user3], self.group1, False, True)

        self.assertEquals(before_state.status_code, 403)
        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_add_user_to_group_members_as_nonmember(self):
        before_state, after_state = self.add_user_to_group(self.user3, [self.user3], self.group1, True, False)

        self.assertEquals(before_state.status_code, 403)
        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_add_user_to_group_admins_as_nonmember(self):
        before_state, after_state = self.add_user_to_group(self.user3, [self.user3], self.group1, False, True)

        self.assertEquals(before_state.status_code, 403)
        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_add_user_to_group_members_as_anonymous(self):
        before_state, after_state = self.add_user_to_group(None, [self.user3], self.group1, True, False)

        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_add_user_to_group_admins_as_anonymous(self):
        before_state, after_state = self.add_user_to_group(None, [self.user3], self.group1, False, True)

        self.assertEquals(after_state.status_code, 403)
        group = ShareGroup.objects.get(id=self.group1.id)
        self.assertNotIn(self.user3.id, group.group_members.all())
        self.assertNotIn(self.user3.id, group.group_admins.all())

    def test_create_dashboard_anonymous(self):
        data = {'name': 'new_dashboard', 'config': self.valid_dashboard_config}
        url = reverse("dashboard-add")
        #self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_create_dashboard_valid_data(self):
        data = {'name': 'new_dashboard', 'config': self.valid_dashboard_config}
        url = reverse("dashboard-add")
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)

    def test_create_dashboard_invalid_data(self):
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        url = reverse("dashboard-add")

        data = {'name': 'new_dashboard', 'config': self.invalid_dashboard_config1}
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 400)

        data = {'name': 'new_dashboard', 'config': self.invalid_dashboard_config2}
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 400)

    def test_create_dashboard_extra_data_stripping(self):
        self.assertTrue(self.client.login(email='user4@localhost', password='00000000'))
        url = reverse("dashboard-add")

        extra_keys_dashboard_config = json.loads(self.valid_dashboard_config)
        extra_keys_dashboard_config['extra'] = "Extra data should be stripped"
        extra_keys_dashboard_config = json.dumps(extra_keys_dashboard_config)

        data = {'name': 'new_dashboard', 'config': extra_keys_dashboard_config}
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 201)
        self.assertNotIn('extra',response.data['config'])
        #TODO: Make sure extra key was stripped




    #TODO: Check responses for values that should not be visible for all users to confirm correct filtering on serializer level