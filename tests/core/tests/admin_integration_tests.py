import os.path

from django.test.client import RequestFactory
from django.test.testcases import TestCase
from django.contrib.auth.models import User
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

from core.admin import BookAdmin
from core.models import Author, Book


class ImportExportAdminIntegrationTest(TestCase):

    def setUp(self):
        user = User.objects.create_user('admin', 'admin@example.com',
                'password')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='password')

    def test_import_export_template(self):
        response = self.client.get('/admin/core/book/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                'admin/import_export/change_list_import_export.html')
        self.assertContains(response, _('Import'))
        self.assertContains(response, _('Export'))

    def test_import(self):
        input_format = '0'
        filename = os.path.join(
                os.path.dirname(__file__),
                os.path.pardir,
                'exports',
                'books.csv')
        data = {
                'input_format': input_format,
                'import_file': open(filename),
                }
        response = self.client.post('/admin/core/book/import/', data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        self.assertFalse(response.context['result'].has_errors())
        self.assertIn('confirm_form', response.context)
        confirm_form = response.context['confirm_form']

        data = confirm_form.initial
        response = self.client.post('/admin/core/book/process_import/', data,
                follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Import finished'))

    def test_export(self):
        response = self.client.get('/admin/core/book/export/')
        self.assertEqual(response.status_code, 200)

        data = {
                'file_format': '0',
                }
        response = self.client.post('/admin/core/book/export/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("Content-Disposition"))

    def test_import_export_buttons_visible_without_add_permission(self):
        # issue 38 - Export button not visible when no add permission
        original = BookAdmin.has_add_permission
        BookAdmin.has_add_permission = lambda self, request: False
        response = self.client.get('/admin/core/book/')
        BookAdmin.has_add_permission = original

        self.assertContains(response, _('Export'))
        self.assertContains(response, _('Import'))


class ExportMixinTest(TestCase):
    """
    Test `ExportMixin`.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.book_admin = BookAdmin(Book, None)  # None for admin site

        self.author1 = Author.objects.create(name='Author 1')
        self.author2 = Author.objects.create(name='Author 2')
        self.book1 = Book.objects.create(name='Book 1', author=self.author1)
        self.book2 = Book.objects.create(name='Book 2', author=self.author2)

    def test_get_export_queryset_all(self):
        """
        `get_export_queryset()` returns all objects by default.
        """
        request = self.factory.post('/admin/core/book/export/')
        self.assertQuerysetEqual(
            self.book_admin.get_export_queryset(request),
            ['<Book: Book 1>', '<Book: Book 2>'],
            ordered=False)

    def test_get_export_queryset_filtered(self):
        """
        `get_export_queryset()` applies the changelist's filtering.
        """
        query = urlencode({'author__id__exact': self.author2.pk})
        request = self.factory.post('/admin/core/book/export/?{0}'.format(query))
        self.assertQuerysetEqual(
            self.book_admin.get_export_queryset(request),
            ['<Book: Book 2>'],
            ordered=False)
