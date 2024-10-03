from django.test import TestCase
from django.urls import reverse
import json


class MessagingTestCase(TestCase):

    def setUp(self):
        self.url = reverse('message_exchange')

    def test_back_and_forth_messaging(self):
        # Simulating message exchanges

        # First message
        response1 = self.client.post(self.url, json.dumps({'message': 'Hello, LLM!'}), content_type='application/json')
        self.assertEqual(response1.status_code, 200)
        json_response1 = response1.json()
        print('User: Hello, LLM!')
        print('LLM:', json_response1['response'])

        # Second message
        response2 = self.client.post(self.url, json.dumps({'message': 'How are you doing?'}),
                                     content_type='application/json')
        self.assertEqual(response2.status_code, 200)
        json_response2 = response2.json()
        print('User: How are you doing?')
        print('LLM:', json_response2['response'])

        # Third message
        response3 = self.client.post(self.url, json.dumps({'message': 'Tell me a joke!'}),
                                     content_type='application/json')
        self.assertEqual(response3.status_code, 200)
        json_response3 = response3.json()
        print('User: Tell me a joke!')
        print('LLM:', json_response3['response'])
