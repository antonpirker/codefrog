from django.db import models

CATEGORY_BUG = 'bug'
CATEGORY_CHANGE = 'change'
CATEGORY_CHOICES = (
    (CATEGORY_BUG, 'Bug-Fix'),
    (CATEGORY_CHANGE, 'Change'),
)

BUG_LABELS = ()

class CategorizationMixin:
    def get_category(self):
        bug_labels = self.project.get_bug_labels()
        for label in self.labels:
            if label in bug_labels:
                return CATEGORY_BUG

        return CATEGORY_CHANGE
