import datetime

from django.test import TestCase

from maintainer.core.utils import daterange, foo


class DateRangeTestCase(TestCase):
    def test_daterange(self):
        start_date = datetime.datetime.now().date()
        end_date = start_date + datetime.timedelta(days=3)

        generator = daterange(start_date, end_date)
        one = next(generator)
        self.assertEqual(one, start_date + datetime.timedelta(days=0))
        two = next(generator)
        self.assertEqual(two, start_date + datetime.timedelta(days=1))
        three = next(generator)
        self.assertEqual(three, start_date + datetime.timedelta(days=2))


class FooTestCase(TestCase):
    def test_foo(self):
        bla = foo(5)
        self.assertEqual(bla, 1)
