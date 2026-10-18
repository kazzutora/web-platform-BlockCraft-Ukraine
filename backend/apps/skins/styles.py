"""Fixed lists behind the skin catalog filters: style tags and colour buckets."""

from django.db import models


class Style(models.TextChoices):
    CASUAL = "casual", "Повсякденний"
    FANTASY = "fantasy", "Фентезі"
    MEDIEVAL = "medieval", "Середньовіччя"
    SCIFI = "scifi", "Наукова фантастика"
    ANIME = "anime", "Аніме"
    HORROR = "horror", "Жахи"
    CUTE = "cute", "Милий"
    MOB = "mob", "Моби"
    MILITARY = "military", "Військовий"
    SPORT = "sport", "Спорт"
    UKRAINIAN = "ukrainian", "Український"


MAX_STYLES = 3


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
