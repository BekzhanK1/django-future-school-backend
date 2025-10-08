import logging
import os
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import Resource

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Resource)
def resource_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for Resource pre-deletion.
    
    This signal is triggered before a Resource object is deleted from the database.
    It logs information about the resource being deleted and its children (if it's a directory).
    
    Args:
        sender: The model class that sent the signal (Resource)
        instance: The Resource instance being deleted
        **kwargs: Additional keyword arguments
    """
    try:
        # Log basic information about the resource being deleted
        logger.info(
            f"Deleting resource: '{instance.title}' (ID: {instance.id}, Type: {instance.type})"
        )
        
        # If it's a directory, log information about its children
        if instance.type == 'directory':
            children_count = instance.children.count()
            if children_count > 0:
                logger.info(
                    f"Directory '{instance.title}' has {children_count} children that will be deleted"
                )
                
                # Log details about child resources
                children = instance.children.all()
                for child in children:
                    logger.info(
                        f"  - Child: '{child.title}' (ID: {child.id}, Type: {child.type})"
                    )
        
        # If it's a file resource, log file information
        elif instance.type == 'file' and instance.file:
            logger.info(
                f"File resource '{instance.title}' has file: {instance.file.name}"
            )
            
    except Exception as e:
        logger.error(f"Error in resource_pre_delete signal: {str(e)}")


@receiver(post_delete, sender=Resource)
def resource_post_delete(sender, instance, **kwargs):
    """
    Signal handler for Resource post-deletion cleanup.
    
    This signal is triggered after a Resource object is deleted from the database.
    It handles cleanup of physical files from the filesystem.
    
    Args:
        sender: The model class that sent the signal (Resource)
        instance: The Resource instance that was deleted
        **kwargs: Additional keyword arguments
    """
    try:
        # Clean up physical file if it exists
        if instance.type == 'file' and instance.file:
            cleanup_physical_file(instance)
        
        # Log successful deletion
        logger.info(
            f"Successfully deleted resource: '{instance.title}' (ID: {instance.id})"
        )
        
    except Exception as e:
        logger.error(f"Error in resource_post_delete signal: {str(e)}")


def cleanup_physical_file(resource_instance):
    """
    Helper function to clean up physical files from the filesystem.
    
    Args:
        resource_instance: The Resource instance containing file information
    """
    try:
        file_path = resource_instance.file.path
        file_name = resource_instance.file.name
        
        if os.path.exists(file_path):
            # Remove the physical file from disk
            os.remove(file_path)
            logger.info(f"Deleted physical file: {file_path}")
        else:
            logger.warning(f"Physical file not found on disk: {file_path}")
            
    except FileNotFoundError:
        logger.warning(f"File not found during cleanup: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied when deleting file: {file_path}")
    except OSError as os_error:
        logger.error(f"OS error when deleting file {file_name}: {str(os_error)}")
    except Exception as file_error:
        logger.error(f"Unexpected error deleting physical file {file_name}: {str(file_error)}")


def get_directory_tree_info(resource_instance):
    """
    Helper function to get detailed information about a directory's structure.
    
    Args:
        resource_instance: The Resource instance (should be a directory)
        
    Returns:
        dict: Information about the directory structure
    """
    if resource_instance.type != 'directory':
        return {}
    
    def count_children_recursively(resource, level=0):
        """Recursively count children in directory tree."""
        result = {
            'files': 0,
            'directories': 0,
            'total_files': 0
        }
        
        for child in resource.children.all():
            if child.type == 'file':
                result['files'] += 1
                result['total_files'] += 1
            elif child.type == 'directory':
                result['directories'] += 1
                child_result = count_children_recursively(child, level + 1)
                result['total_files'] += child_result['total_files']
        
        return result
    
    return count_children_recursively(resource_instance)
