CATEGORY_BUG = "bug"
CATEGORY_CHANGE = "change"

CATEGORY_CHOICES = (
    (CATEGORY_BUG, "Bug-Fix"),
    (CATEGORY_CHANGE, "Change"),
)


class CategorizationMixin:
    def get_category(self):
        bug_labels = self.project.get_bug_labels()
        for label in self.labels:
            if label in bug_labels:
                return CATEGORY_BUG

        for label in self.labels:
            for bug_label in bug_labels:
                if bug_label in label:
                    return CATEGORY_BUG

        return CATEGORY_CHANGE

    def save(self, *args, **kwargs):
        self.category = self.get_category()
        super().save(*args, **kwargs)
