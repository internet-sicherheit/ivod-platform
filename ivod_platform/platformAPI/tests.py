from rest_framework.test import APITestCase
from django.shortcuts import reverse
from .permissions import *
# Create your tests here.


class PlatformAPITestCase(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", email=None, password="00000000")
        self.user1 = User.objects.create_user(username="user1", email=None, password="00000000")
        self.user2 = User.objects.create_user(username="user2", email=None, password="00000000")
        #Use user3 for a authenticated, but otherwise no permissions
        self.user3 = User.objects.create_user(username="user3", email=None, password="00000000")
        self.user4 = User.objects.create_user(username="user4", email=None, password="00000000")

        self.group1 = Group.objects.create(name="group1")
        self.group2 = Group.objects.create(name="group2")
        self.group1.user_set.add(self.user4)


        self.datasource1 = Datasource.objects.create(source="file://some/file1", scope_path="/file1", owner=self.user1)
        self.datasource2 = Datasource.objects.create(source="file://some/file2", scope_path="/file2", owner=self.user2)

        self.chart1 = Chart.objects.create(
            chart_name="piechart",
            scope_path="/piechart1",
            owner=self.user1,
            original_datasource=self.datasource1,
            config="{}",
            downloadable=True,
            visibility=Chart.VISIBILITY_PRIVATE)

        self.chart2 = Chart.objects.create(
            chart_name="piechart",
            scope_path="/piechart2",
            owner=self.user1,
            original_datasource=self.datasource1,
            config="{}",
            downloadable=False,
            visibility=Chart.VISIBILITY_SHARED)

        self.chart3 = Chart.objects.create(
            chart_name="barchart",
            scope_path="/barchart1",
            owner=self.user2,
            original_datasource=self.datasource2,
            config="{}",
            downloadable=True,
            visibility=Chart.VISIBILITY_PRIVATE)

        self.chart4 = Chart.objects.create(
            chart_name="barchart",
            scope_path="/barchart2",
            owner=self.user2,
            original_datasource=self.datasource2,
            config="{}",
            downloadable=True,
            visibility=Chart.VISIBILITY_PRIVATE)

        self.chart5 = Chart.objects.create(
            chart_name="barchart",
            scope_path="/barchart3",
            owner=self.user2,
            original_datasource=self.datasource2,
            config="{}",
            downloadable=True,
            visibility=Chart.VISIBILITY_PUBLIC)

        self.chart2.shared_users.add(self.user2)
        self.chart2.shared_groups.add(self.group1)
        self.chart2.shared_groups.add(self.group2)
        self.chart2.save()
        self.datasource1.shared_users.add(self.user2)
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
        self.assertEquals(response.data[0]["scope_path"], "/barchart3")

    def test_chart_read_not_shared_not_owned(self):
        # Access a chart directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_read_shared(self):
        # Access a chart directly by its key, with it being shared -> Success
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
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

    def test_datasource_read_not_shared_not_owned(self):
        # Access a datasource directly by its key, without access rights -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_read_shared(self):
        # Access a datasource directly by its key, with it being shared -> Success
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
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

    def test_chart_delete_authenticated_public_only(self):
        # Delete a chart directly by its key, with it being public -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
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

    def test_chart_delete_shared(self):
        # Delete a chart directly by its key, with it being shared -> Error 403
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
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

    def test_chart_edit_shared(self):
        # Modify shared chart in a legal way -> Error 403
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
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

        data = {'config': 'new config'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['config'], 'new config')

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
                'chart_name': 'TESTNAME',
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


    def test_add_user_to_share_as_shared(self):
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_add_user_to_share_authenticated_only(self):
        data = {'users': [self.user3.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_user_from_share_as_owner(self):
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))

        data_before = self.client.get(url, format='json')
        self.assertEquals(data_before.data['users'], [self.user2.id])

        response = self.client.delete(url, data, format='json')
        data_after = response.data
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data_after['users']), 0)


    def test_del_shared_from_share_as_shared(self):
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_shared_from_share_authenticated_only(self):
        data = {'users': [self.user2.id]}
        url = reverse("chart-shared", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))

        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_del_not_shared_user_from_share_as_owner(self):
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

    def test_share_with_already_shared_user_from_share_as_owner(self):
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

    def test_chart_access_after_share(self):
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

    #TODO: When sharing, check if groups are unaffected by actions on users and vice versa

    #TODO: Check responses for values that should not be visible for all users to confirm correct filtering on serializer level

    #TODO: Differentiate between direct-share and group share
