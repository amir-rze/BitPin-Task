import random
from django.core.management.base import BaseCommand
from faker import Faker
from BitPin.apps.rating.models import Article, Rating
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populate the database with random articles and ratings'

    def add_arguments(self, parser):
        parser.add_argument('num_articles', type=int, help='The number of articles to create')
        parser.add_argument('num_ratings', type=int, help='The number of ratings to create per article')

    def handle(self, *args, **kwargs):
        fake = Faker()
        num_articles = kwargs['num_articles']
        num_ratings = kwargs['num_ratings']

        for _ in range(num_articles):
            article = Article.objects.create(
                title=fake.sentence(nb_words=6),
                content=fake.paragraph(nb_sentences=10),
                created_at=timezone.now(),
                updated_at=timezone.now(),
                num_ratings=0,  # Start with 0 ratings
                average_rating=0.0,
                last_rating_time=None
            )
            self.stdout.write(self.style.SUCCESS(f'Created Article: {article.title}'))

            # Generate random ratings for the article
            user_ids = set()  # To ensure unique user_id per article
            for _ in range(num_ratings):
                user_id = random.randint(1, 1000)  # Simulating random user IDs between 1 and 1000
                while user_id in user_ids:
                    user_id = random.randint(1, 1000)  # Ensure unique user_id for each rating
                user_ids.add(user_id)

                score = random.randint(0, 5)  # Random score between 1 and 5

                Rating.objects.create(
                    article=article,
                    user_id=user_id,
                    score=score,
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )

                article.num_ratings += 1
                article.average_rating = (
                    (article.average_rating * (article.num_ratings - 1) + score) / article.num_ratings
                )
                article.last_rating_time = timezone.now()
                article.save()

            self.stdout.write(self.style.SUCCESS(f'Added {num_ratings} ratings for article "{article.title}"'))

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {num_articles} articles and {num_articles * num_ratings} ratings.'))
