"""Association tables for many-to-many relationships in PromptVault.

This module defines junction tables for many-to-many relationships.
Currently includes the prompt_tags association table.
"""

from sqlalchemy import Table, Column, Integer, ForeignKey, Index

from src.db.base import Base


# Many-to-many association table between prompts and tags
prompt_tags = Table(
    'prompt_tags',
    Base.metadata,
    Column('prompt_id', Integer, ForeignKey('prompts.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_prompt_tags_tag', 'tag_id')
)
