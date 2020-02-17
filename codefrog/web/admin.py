from django.contrib import admin

from web.models import Usage, Plan, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'newly_registered', 'plan', 'date_joined',
    )
    list_filter = (
        'user', 'newly_registered', 'plan', 'date_joined',
    )
    ordering = ['-date_joined', ]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'has_trial_period', 'free_trial_days',
    )
    list_filter = (
        'name', 'slug', 'has_trial_period', 'free_trial_days',
    )
    ordering = ['name', ]


@admin.register(Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'user', 'timestamp', 'action',
    )
    list_filter = (
        'project', 'user', 'timestamp', 'action',
    )
    ordering = ['-timestamp', ]
