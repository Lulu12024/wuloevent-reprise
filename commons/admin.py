from django.contrib.admin import ModelAdmin

from django.core.paginator import Paginator


class NoCountPaginator(Paginator):
    @property
    def count(self):
        return 999999999  # Some arbitrarily large number,
        # so we can still get our page tab.


class BaseModelAdmin(ModelAdmin):
    exclude = ('deleted_at', 'is_deleted', 'restored_at')
    ordering = ['-timestamp']
    paginator = NoCountPaginator
    show_full_result_count = False
