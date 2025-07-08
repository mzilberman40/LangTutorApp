# In learning/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LexicalUnit, LexicalUnitTranslation, Phrase
from .tasks import (
    validate_lu_integrity_async,
    verify_translation_link_async,
    enrich_phrase_async,
)


@receiver(
    post_save,
    sender=LexicalUnit,
    dispatch_uid="trigger_lu_validation_on_lexical_unit_save",
)
def trigger_lu_validation(sender, instance, created, update_fields=None, **kwargs):
    """
    Triggers the asynchronous validation task after a LexicalUnit is saved,
    but avoids recursion if the save was part of the validation task itself.
    """
    if update_fields and "validation_status" in update_fields:
        return

    validate_lu_integrity_async.delay(instance.id)


@receiver(
    post_save,
    sender=LexicalUnitTranslation,
    dispatch_uid="trigger_translation_link_verification_on_create",
)
def trigger_translation_link_verification(sender, instance, created, **kwargs):
    """
    Triggers the asynchronous verification task only when a new
    LexicalUnitTranslation link is first created.
    """
    # Мы запускаем задачу только при создании новой связи (`created` is True),
    # чтобы избежать ее повторного запуска, когда задача сама обновляет
    # статус валидации в этой же модели.
    if created:
        verify_translation_link_async.delay(instance.id)


@receiver(post_save, sender=Phrase, dispatch_uid="trigger_phrase_enrichment_on_create")
def trigger_phrase_enrichment(sender, instance, created, **kwargs):
    """
    Triggers the asynchronous enrichment task only when a new Phrase
    object is first created.
    """
    if created:
        enrich_phrase_async.delay(phrase_id=instance.id)
