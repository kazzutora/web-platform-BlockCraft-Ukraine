"""Colour buckets behind the skin catalog filter (computed from the texture)."""

from django.db import models


class ColorBucket(models.TextChoices):
    RED = "red", "Червоний"
    ORANGE = "orange", "Помаранчевий"
    YELLOW = "yellow", "Жовтий"
    GREEN = "green", "Зелений"
    CYAN = "cyan", "Бірюзовий"
    BLUE = "blue", "Синій"
    PURPLE = "purple", "Фіолетовий"
    PINK = "pink", "Рожевий"
    BROWN = "brown", "Коричневий"
    BLACK = "black", "Чорний"
    WHITE = "white", "Білий"
    GRAY = "gray", "Сірий"
