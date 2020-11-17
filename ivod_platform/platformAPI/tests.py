from django.test import TestCase
from rest_framework.test import APITestCase
# Create your tests here.


 #class PlatformAPITestCase(APITestCase)
 # def test_user_login_and_update(self):
 #        data = {
 #            'username': 'testcfeuser',
 #            'password': 'somerandopassword'
 #        }
 #        url = api_reverse("api-login")
 #        response = self.client.post(url, data)
 #        self.assertEqual(response.status_code, status.HTTP_200_OK)
 #        token = response.data.get("token")
 #        if token is not None:
 #            blog_post = BlogPost.objects.first()
 #            #print(blog_post.content)
 #            url = blog_post.get_api_url()
 #            data = {"title": "Some rando title", "content": "some more content"}
 #            self.client.credentials(HTTP_AUTHORIZATION='JWT ' + token) # JWT <token>
 #            response = self.client.put(url, data, format='json')
 #            self.assertEqual(response.status_code, status.HTTP_200_OK)
