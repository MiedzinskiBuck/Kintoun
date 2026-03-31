import unittest
from unittest.mock import Mock

from functions.create_client import Client


class TestCreateClient(unittest.TestCase):
    def test_create_client_with_region(self):
        session = Mock()
        session.client.return_value = "client"

        client = Client("cfg", session, "s3", "us-east-1").create_aws_client()

        self.assertEqual(client, "client")
        session.client.assert_called_once_with("s3", config="cfg", region_name="us-east-1")

    def test_create_client_without_region(self):
        session = Mock()
        session.client.return_value = "client"

        client = Client("cfg", session, "s3").create_aws_client()

        self.assertEqual(client, "client")
        session.client.assert_called_once_with("s3", config="cfg")


if __name__ == "__main__":
    unittest.main()
