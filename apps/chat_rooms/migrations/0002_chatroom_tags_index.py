# -*- coding: utf-8 -*-
"""
Migration pour optimiser les performances des requêtes sur les tags.
"""

from django.contrib.postgres.indexes import GinIndex
from django.db import migrations

class Migration(migrations.Migration):
    """
    Ajoute un index GIN sur le champ tags pour améliorer les performances
    des recherches sur les tags dans les salons de discussion.
    
    Cette optimisation est cruciale pour une application à grande échelle
    avec des millions d'utilisateurs.
    """

    dependencies = [
        ('chat_rooms', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='chatroom',
            index=GinIndex(
                fields=['tags'],
                name='chatroom_tags_gin_idx',
                opclasses=['jsonb_path_ops']
            ),
        ),
    ]
