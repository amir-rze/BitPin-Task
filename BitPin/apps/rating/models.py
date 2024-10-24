from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Article(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    num_ratings = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Rating(models.Model):
    article = models.ForeignKey(Article,related_name='ratings', on_delete=models.CASCADE)
    user_id = models.IntegerField()
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = (('article', 'user_id'),)
        indexes = [
            models.Index(fields=['user_id']),
        ]