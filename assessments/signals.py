import logging
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Test

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Test)
def test_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for Test pre-deletion.
    Deletes synced derived tests (clones) before this template test is deleted.
    """
    try:
        if hasattr(instance, 'derived_tests'):
            synced_clones = instance.derived_tests.filter(is_unlinked_from_template=False)
            if synced_clones.exists():
                logger.info(f"Deleting {synced_clones.count()} synced derived tests for template '{instance.title}'")
                for clone in synced_clones:
                    clone.delete()
    except Exception as e:
        logger.error(f"Error in test_pre_delete signal: {str(e)}")
