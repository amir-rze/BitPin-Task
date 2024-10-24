import random
from django.core.management.base import BaseCommand
from faker import Faker
from BitPin.apps.rating.models import Article, Rating
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populate the database with random articles and ratings'

    def add_arguments(self, parser):
        parser.add_argument('num_articles', type=int, help='The number of articles to create')

    def handle(self, *args, **kwargs):
        fake = Faker()
        num_articles = kwargs['num_articles']

        for _ in range(num_articles):
            article = Article.objects.create(
                title=fake.sentence(nb_words=6),
                content=fake.paragraph(nb_sentences=10),
                created_at=timezone.now(),
                updated_at=timezone.now(),
                num_ratings=0,  # Start with 0 ratings
                avg_rating=0.0,
            )
            self.stdout.write(self.style.SUCCESS('Created Article: {article.title}'))


        self.stdout.write(self.style.SUCCESS(f'Successfully populated {num_articles}'))
