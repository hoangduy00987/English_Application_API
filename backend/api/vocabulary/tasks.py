from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from ..submodels.models_vocabulary import UserVocabularyProcess

@shared_task
def update_review_status():
   
    now = timezone.now()
    processes = UserVocabularyProcess.objects.filter(
        is_learned=True, last_learned_at__lt=now - timedelta(seconds=30)
    )
    
    for process in processes:
        process.is_need_review = True
        process.save()
    return f"{processes.count()} vocabulary processes updated for review."