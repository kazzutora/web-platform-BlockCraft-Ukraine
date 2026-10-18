from django.db import migrations

# Roots are searched inside words, so each one is long or rare enough not to hit ordinary
# words (no «ебат»: «дебати»; no «бля»: «бляха»). Short ambiguous words match only whole.
ROOTS = {
    "uk": ["хуй", "хуя", "хує", "хуї", "пизд", "пізд", "бляд", "блят", "єбан", "їбан", "їбал",
           "мудак", "мудил", "підор", "підар", "залуп", "гандон", "шлюх", "шльондр"],
    "ru": ["хуе", "хуё", "ебан", "ёбан", "ебал", "ебло", "пидор", "пидар", "уебок", "уёбок"],
    "en": ["fuck", "shit", "nigger", "nigga", "faggot", "cunt", "whore", "pizd", "blyad",
           "blyat", "yebat", "mudak", "zalupa", "gandon", "shluha", "hitler"],
}  # fmt: skip
WHOLE_WORDS = {
    "uk": ["сука", "суки", "сучка", "курва", "курви", "срака"],
    "ru": ["сучара", "жопа"],
    "en": ["bitch", "slut", "dick"],
}


def seed(apps, schema_editor):
    BannedWord = apps.get_model("moderation", "BannedWord")
    rows = [
        BannedWord(word=word, language=language, is_root=is_root)
        for words, is_root in ((ROOTS, True), (WHOLE_WORDS, False))
        for language, items in words.items()
        for word in items
    ]
    BannedWord.objects.bulk_create(rows, ignore_conflicts=True)


def unseed(apps, schema_editor):
    BannedWord = apps.get_model("moderation", "BannedWord")
    words = [word for group in (ROOTS, WHOLE_WORDS) for items in group.values() for word in items]
    BannedWord.objects.filter(word__in=words).delete()


class Migration(migrations.Migration):
    dependencies = [("moderation", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
