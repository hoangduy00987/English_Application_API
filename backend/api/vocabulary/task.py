from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from submodels.models_vocabulary import UserVocabularyProcess

@shared_task
def mark_vocabulary_for_review():
    time_review = timezone.now() - timedelta(hours=24)
    vocabularies = UserVocabularyProcess.objects.filter(last_learned_at=time_review,is_need_review=False)

    for vocab in vocabularies:
        vocab.is_need_review = True
        vocab.save()

    return f"{vocabularies.count()} Vocabulary marked for reviews"