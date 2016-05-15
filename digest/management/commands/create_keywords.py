# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from html.parser import HTMLParser

from django.conf import settings
from django.core.management.base import BaseCommand
from django_q.tasks import async

from digest.alchemyapi import AlchemyAPI
from digest.models import Item
# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_keywords(api, text) -> list:
    response = api.keywords('text', text, {'sentiment': 1})
    result = []
    if response['status'] == 'OK' and 'keywords' in response:
        result = [x['text'] for x in response['keywords'] if len(x['text']) < 30]
    return result


def create_keywords(api, item):
    if item.article_path and os.path.exists(item.article_path):
        logger.info('Process: %s', item.pk)
        with open(item.article_path) as fio:
            keywords = get_keywords(api, strip_tags(fio.read()))
            item.keywords.add(*keywords)


class Command(BaseCommand):
    help = 'Create dataset'

    def add_arguments(self, parser):
        parser.add_argument('start', type=int)
        parser.add_argument('end', type=int)

    def handle(self, *args, **options):
        """
        Основной метод - точка входа
        """
        api = AlchemyAPI(settings.ALCHEMY_KEY)
        pk_limits = (options['start'], options['end'])
        for item in Item.objects.filter(pk__range=pk_limits, keywords=None):
            # create_keywords(api, item)
            async(create_keywords, api, item)
