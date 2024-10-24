from celery import shared_task
from django.db import transaction
from django.db.models import F
from datetime import datetime
import logging
from .models import Article
from django.core.cache import cache
from redis import Redis
from BitPin.settings import REDIS_PORT, REDIS_HOST

logger = logging.getLogger(__name__)

r = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)


@shared_task
def sync_articles_from_redis():
    try:
        # Get all article keys from Redis
        article_keys = r.keys("article_*")

        if not article_keys:
            logger.info("No articles found in Redis cache")
            return

        # Prepare bulk updates
        articles_to_update = []
        for key in article_keys:
            try:
                # Get article data from Redis
                article_data = r.hgetall(key)

                if not article_data:
                    continue

                # Convert Redis byte strings to Python types
                article_data = {k.decode(): v.decode() for k, v in article_data.items()}

                # Extract article_id from key
                article_id = key.decode().split('_')[1]

                articles_to_update.append({
                    'id': article_id,
                    'avg_rating': float(article_data.get('avg_rating', 0)),
                    'num_ratings': int(article_data.get('num_ratings', 0)),
                    'last_rating_time': article_data.get('last_rating_time'),
                    'last_score': float(article_data.get('last_score', 0))
                })

            except (ValueError, KeyError, AttributeError) as e:
                logger.error(f"Error processing article key {key}: {str(e)}")
                continue

        if not articles_to_update:
            logger.info("No valid articles to update")
            return

        # bulk update
        with transaction.atomic():
            for article_data in articles_to_update:
                Article.objects.filter(id=article_data['id']).update(
                    avg_rating=article_data['avg_rating'],
                    num_ratings=article_data['num_ratings'],
                    last_rating_time=article_data['last_rating_time'] if article_data[
                                                                             'last_rating_time'] != "None" else None,
                    last_score=article_data['last_score']
                )

        logger.info(f"Successfully synchronized {len(articles_to_update)} articles from Redis to database")

    except Exception as e:
        logger.error(f"Error in sync_articles_from_redis task: {str(e)}")
        raise
