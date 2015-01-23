#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from os.path import join, dirname
import sys
import warnings

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django
from django.test.client import Client
from django.utils import unittest
from django.utils.encoding import smart_str
from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ImproperlyConfigured

from selenium.webdriver.phantomjs.webdriver import WebDriver

import django_js_reverse
from django_js_reverse import save_js_file

# Raise errors on DeprecationWarnings
# warnings.simplefilter('error', DeprecationWarning)



class JSReverseViewTestCaseMinified(TestCase):
    client = None
    urls = 'django_js_reverse.tests.test_urls'

    @classmethod
    def setUpClass(cls):
        if hasattr(django, 'setup'):
            # for django >= 1.7
            django.setup()
        cls.selenium = WebDriver()
        super(JSReverseViewTestCaseMinified, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(JSReverseViewTestCaseMinified, cls).tearDownClass()

    def setUp(self):
        self.client = Client()

    def assertEqualJSUrlEval(self, url_call, expected_url):
        response = self.client.post('/jsreverse/')
        self.assertEqual(self.selenium.execute_script('%s return %s;' % (smart_str(response.content), url_call)),
                         expected_url)

    def test_view_no_url_args(self):
        self.assertEqualJSUrlEval('Urls.test_no_url_args()', '/test_no_url_args/')

    def test_view_one_url_arg(self):
        self.assertEqualJSUrlEval('Urls.test_one_url_args("arg_one")', '/test_one_url_args/arg_one/')

    def test_view_two_url_args(self):
        self.assertEqualJSUrlEval('Urls.test_two_url_args("arg_one", "arg_two")', '/test_two_url_args/arg_one-arg_two/')

    def test_view_optional_url_arg(self):
        self.assertEqualJSUrlEval('Urls.test_optional_url_arg("arg_two")',
                                  '/test_optional_url_arg/2_arg_two/')
        self.assertEqualJSUrlEval('Urls.test_optional_url_arg("arg_one", "arg_two")',
                                  '/test_optional_url_arg/1_arg_one-2_arg_two/')

    def test_unicode_url_name(self):
        self.assertEqualJSUrlEval('Urls.test_unicode_url_name()', '/test_unicode_url_name/')

    @override_settings(JS_REVERSE_JS_VAR_NAME='Foo')
    def test_js_var_name_changed_valid(self):
        # This test overrides JS_REVERSE_JS_VAR_NAME permanent, so it's disabled by default.
        # Needs to by tested as single test case
        self.assertEqualJSUrlEval('Foo.test_no_url_args()', '/test_no_url_args/')

    @override_settings(JS_REVERSE_JS_VAR_NAME='1test')
    def test_js_var_name_changed_to_invalid(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/jsreverse/')

    def test_namespaces(self):
        self.assertEqualJSUrlEval('Urls["ns1:test_two_url_args"]("arg_one", "arg_two")',
                                  '/ns1/test_two_url_args/arg_one-arg_two/')
        self.assertEqualJSUrlEval('Urls["ns2:test_two_url_args"]("arg_one", "arg_two")',
                                  '/ns2/test_two_url_args/arg_one-arg_two/')

    def test_namespaces_with_args(self):
        self.assertEqualJSUrlEval('Urls["ns_arg:test_two_url_args"]("arg_one", "arg_two", "arg_three")',
                                  '/nsarg_one/test_two_url_args/arg_two-arg_three/')

    def test_namespaces_nested(self):
        self.assertEqualJSUrlEval('Urls["nestedns:ns1:test_two_url_args"]("arg_one", "arg_two")',
                                  '/nestedns/ns1/test_two_url_args/arg_one-arg_two/')

    def test_content_type(self):
        response = self.client.post('/jsreverse/')
        self.assertEqual(response['Content-Type'], 'application/javascript')

    @override_settings(JS_REVERSE_JS_MINIFY='invalid')
    def test_js_minfiy_changed_to_invalid(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/jsreverse/')


@override_settings(JS_REVERSE_JS_MINIFY=False)
class JSReverseViewTestCaseNotMinified(JSReverseViewTestCaseMinified):
    def test_minification(self):
        js_not_minified = smart_str(self.client.post('/jsreverse/').content)
        with override_settings(JS_REVERSE_JS_MINIFY=True):
            js_minified = smart_str(self.client.post('/jsreverse/').content)
            self.assertTrue(len(js_minified) < len(js_not_minified))


class JSReverseStaticFileSaveTest(JSReverseViewTestCaseMinified):
    def test_reverse_js_file_save(self):
        save_js_file()

        package_path = dirname(django_js_reverse.__file__)
        path = join(package_path, 'static', 'django_js_reverse', 'js', 'reverse.js')
        f = open(path)
        content1 = f.read()
        if hasattr(content1, 'decode'):
            content1 = content1.decode()

        r2 = self.client.get('/jsreverse/')
        content2 = r2.content
        if hasattr(content2, 'decode'):
            content2 = content2.decode()

        self.assertEqual(len(content1), len(content2), 'Static file don\'t match http response content_1')
        self.assertEqual(content1, content2, 'Static file don\'t match http response content_2')


class JSReverseNamespaceExcludeTest(JSReverseViewTestCaseMinified):
    def test_namespace_in_urls(self):
        response = self.client.get('/jsreverse/')
        self.assertContains(response, 'exclude_namespace', status_code=200)

    @override_settings(JS_REVERSE_EXCLUDE_NAMESPACES=['exclude_namespace'])
    def test_namespace_not_in_response(self):
        response = self.client.get('/jsreverse/')
        self.assertNotContains(response, 'exclude_namespace', status_code=200)


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + os.sep)
    unittest.main()
