from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
 
from .models import (
    MetadataRecord,
    ProvenanceTag,
    QAQCConfirmation,
    RecordVersion,
)
 
# Records are created through the API so they pass gap detection and validation.
# The admin is therefore view-only: it is for inspecting data, not for editing it.
 
 
class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return False
 
    def has_change_permission(self, request, obj=None):
        return False
 
    def has_delete_permission(self, request, obj=None):
        return False
 
 
class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True
 
    def has_add_permission(self, request, obj=None):
        return False
 
    def has_change_permission(self, request, obj=None):
        return False
 
    def has_delete_permission(self, request, obj=None):
        return False
 
 
class VersionInline(ReadOnlyInline):
    model = RecordVersion
    fields = ("version_number", "created_by", "created_at")
 
 
class QAQCConfirmationInline(ReadOnlyInline):
    model = QAQCConfirmation
    fields = ("version", "confirmed_by", "confirmed_at", "checks")
 
 
class ProvenanceTagInline(ReadOnlyInline):
    model = ProvenanceTag
    fields = ("field_name", "source", "detail")
 
 
@admin.register(MetadataRecord)
class MetadataRecordAdmin(ReadOnlyAdminMixin, GISModelAdmin):
    list_display = ("identifier", "title", "status", "current_version",
                   "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("identifier",)
    inlines = [VersionInline, QAQCConfirmationInline]
 
    # Allow deleting test records during development (cascades to versions etc.)
    def has_delete_permission(self, request, obj=None):
        return True
 
    @admin.display(description="Title")
    def title(self, obj):
        return obj.content.get("title", "")
 
 
@admin.register(RecordVersion)
class RecordVersionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("record", "version_number", "created_by", "created_at")
    list_filter = ("created_at",)
    inlines = [ProvenanceTagInline]
 
 
@admin.register(ProvenanceTag)
class ProvenanceTagAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("version", "field_name", "source", "detail")
    list_filter = ("source", "field_name")
 
 
@admin.register(QAQCConfirmation)
class QAQCConfirmationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("record", "version", "confirmed_by", "confirmed_at")
    list_filter = ("confirmed_at",)