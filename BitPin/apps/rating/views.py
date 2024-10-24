import json
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from .models import Article, Rating
from django.db.models import Avg, Count
from django.db import transaction
import redis
from django.utils import timezone
from .classes import ArticlePagination
from BitPin.settings import REDIS_HOST, REDIS_PORT

USER_RATING_CACHE_TTL = 60 * 60  # 1 hour
ARTICLE_CACHE_TTL = 10 * 60  # 10 minutes
CACHE_TTL = 60 * 15  # 15 minutes cache TTL
OUTLIER_THRESHOLD = 2
NUM_RATING_THRESHOLD = 50

MIN_TIME_WINDOW_SECOND = 5

# Initialize Redis
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)


class RatingView(APIView):

    def calculate_dynamic_alpha(self, old_ema, score, last_score, last_rating_time, _time,
                                K=86400):  # Default K = 86400 seconds (1 day)

        if isinstance(last_rating_time, str):
            last_rating_time = datetime.fromisoformat(last_rating_time.replace('Z', '+00:00'))

        if isinstance(_time, str):
            _time = datetime.fromisoformat(_time.replace('Z', '+00:00'))

        if last_rating_time:
            time_diff = _time - last_rating_time
            time_diff_seconds = time_diff.total_seconds()

            alpha = time_diff_seconds / (K + time_diff_seconds)

            if time_diff_seconds < MIN_TIME_WINDOW_SECOND and score == last_score and abs(
                    old_ema - score) > OUTLIER_THRESHOLD:
                alpha /= abs(old_ema - score)
        else:
            alpha = 1

        return alpha

    def get_article_from_cache(self, article_id):

        cache_key = f"article_{article_id}"
        cached_article = r.hgetall(cache_key)

        if cached_article:
            article_data = {k.decode(): v.decode() for k, v in cached_article.items()}
            article_data['num_ratings'] = int(article_data['num_ratings'])
            article_data['avg_rating'] = float(article_data['avg_rating'])
            article_data['last_score'] = int(article_data['last_score'])
            article_data['last_rating_time'] = None if article_data['last_rating_time'] == "None" else article_data[
                'last_rating_time']
            return article_data

        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return None

        article_data = {
            "id": article_id,
            "num_ratings": 0,
            "avg_rating": 0.0,
            'last_score': -1,
            "last_rating_time": "None"
        }

        r.hset(name=cache_key, mapping=article_data)
        return article_data

    def post(self, request, article_id):

        user_id = request.data.get('user_id')
        score = request.data.get('score')

        if not (0 <= score <= 5):
            return Response({'error': 'Score must be between 0 and 5'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            rating, created = Rating.objects.update_or_create(
                article_id=article_id, user_id=user_id,
                defaults={'score': score}
            )

        article_data = self.get_article_from_cache(article_id)
        if not article_data:
            return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)
        print(article_data)
        _time = timezone.now()
        alpha = self.calculate_dynamic_alpha(article_data['avg_rating'], score, article_data['last_score'],
                                             article_data['last_rating_time'], _time)
        new_ema = article_data['avg_rating'] * (1 - alpha) + score * alpha

        cache_key = f"article_{article_id}"
        r.hset(name=cache_key, mapping={
            "id": article_id,
            "last_score": score,
            "num_ratings": article_data['num_ratings'] + 1 if created else article_data['num_ratings'],
            "avg_rating": new_ema,
            "last_rating_time": _time.isoformat()
        })

        return Response({
            'detail': 'Rating submitted successfully',
        }, status=status.HTTP_200_OK)


class ArticleListView(APIView):
    pagination_class = ArticlePagination

    def get(self, request):
        user_id = request.query_params.get('user_id')

        cached_article_list = r.get('article_list')

        if cached_article_list:
            article_list = json.loads(
                cached_article_list)
        else:
            articles = Article.objects.all().values('id', 'title', 'num_ratings', 'avg_rating')

            article_list = []
            for article in articles:
                article_data = {
                    'id': article['id'],
                    'title': article['title'],
                    'num_ratings': article['num_ratings'],
                    'avg_rating': article['avg_rating'],
                    'user_rating': None
                }
                article_list.append(article_data)

            r.set('article_list', json.dumps(article_list), ex=ARTICLE_CACHE_TTL)

        if user_id:
            user_rating_key = f"user_ratings_{user_id}"
            cached_user_ratings = r.hgetall(user_rating_key)

            if cached_user_ratings:
                user_ratings = {int(k): int(v) for k, v in
                                cached_user_ratings.items()}
            else:
                user_ratings = Rating.objects.filter(user_id=user_id).values_list('article_id', 'score')
                user_ratings = {article_id: score for article_id, score in user_ratings}

                if user_ratings:
                    r.set(user_rating_key, json.dumps(user_ratings), ex=USER_RATING_CACHE_TTL)

            for article_data in article_list:
                article_id = article_data['id']
                article_data['user_rating'] = user_ratings.get(article_id, None)  # None if no user rating exists

        paginator = self.pagination_class()
        paginated_articles = paginator.paginate_queryset(article_list, request)
        return paginator.get_paginated_response(paginated_articles)
