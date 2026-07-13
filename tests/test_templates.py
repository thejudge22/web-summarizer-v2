import asyncio
import unittest
from unittest.mock import Mock, patch

from main import home, summary


class TemplateRouteTests(unittest.TestCase):
    @patch("main.templates.TemplateResponse")
    def test_home_uses_request_first_template_response_signature(self, template_response):
        request = Mock()
        expected_response = Mock()
        template_response.return_value = expected_response

        response = asyncio.run(home(request))

        self.assertIs(response, expected_response)
        template_response.assert_called_once_with(request=request, name="index.html")

    @patch("main.templates.TemplateResponse")
    def test_summary_uses_request_first_template_response_signature(self, template_response):
        request = Mock()
        expected_response = Mock()
        template_response.return_value = expected_response

        response = asyncio.run(summary(request, "https://example.com"))

        self.assertIs(response, expected_response)
        template_response.assert_called_once_with(
            request=request,
            name="loading.html",
            context={"url": "https://example.com"},
        )
