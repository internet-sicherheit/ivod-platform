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

        euser2 = EnhancedUser.objects.get(auth_user=self.user2)
        euser2.charts_shared_with_user.add(self.chart2)
        euser2.datasources_shared_with_user.add(self.datasource1)
        euser2.save()

    def test_datasources_list_unautenticated(self):
        data = {}
        url = reverse("datasource-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_list_unautenticated(self):
        data = {}
        url = reverse("chart-add")
        response = self.client.get(url,data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_list_authenticated(self):
        data = {}
        url = reverse("datasource-add")
        self.client.login(username='user3', password='00000000')
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response_obj = response.data
        self.assertEquals(len(response_obj), 0)

    def test_chart_list_authenticated_public_only(self):
        data = {}
        url = reverse("chart-add")
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        #There is 1 public chart in the database
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]["scope_path"], "/barchart3")

    def test_chart_read_not_shared_not_owned(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_read_shared(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/piechart2")

    def test_chart_read_owned(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk':self.chart2.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/piechart2")

    def test_datasource_read_not_shared_not_owned(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_datasource_read_shared(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/file1")

    def test_datasource_read_owned(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data["scope_path"], "/file1")

    def test_chart_delete_authenticated_public_only(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        data = {}
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)

    def test_datasource_delete_authenticated_only(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_shared(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_delete_owned(self):
        data = {}
        url = reverse("datasource-get", kwargs={'pk': self.datasource1.id})
        self.assertTrue(self.client.login(username='user1', password='00000000'))
        response = self.client.delete(url, data, format='json')
        self.assertEquals(response.status_code, 204)
        url = reverse("chart-get", kwargs={'pk': self.chart1.id})
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_chart_edit_authenticated_public_only(self):
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart5.id})
        self.assertTrue(self.client.login(username='user3', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_shared(self):
        data = {'scope_path': '/new/scope'}
        url = reverse("chart-get", kwargs={'pk': self.chart2.id})
        self.assertTrue(self.client.login(username='user2', password='00000000'))
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 403)

    def test_chart_edit_owned(self):
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

        data = {'chart_name': 'SHOULD BE READ ONLY'}
        response = self.client.patch(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        response = self.client.get(url, data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertNotEqual(response.data['chart_name'], 'SHOULD BE READ ONLY')

    #TODO: Differentiate between direct-share and group share
