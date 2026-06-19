"""
AeroLux Select — Admin Configuration
Configuration de l'interface d'administration Django pour tous les modèles core.
"""

from django.contrib import admin
from django.utils.html import format_html

from core.models import (
    Site,
    Airport,
    Destination,
    PricingRule,
    AirportCategoryPrice,
    VehicleCategory,
    Vehicle,
    PremiumAddOn,
    Booking,
    SiteContent,
    Testimonial,
    SiteSettings,
    ProfitReport,
    BookingPayment,
    EmailTemplate,
)


# ──────────────────────────────────────────────
#  Inline admins
# ──────────────────────────────────────────────

class AirportInline(admin.TabularInline):
    model = Airport
    extra = 0
    fields = ('code', 'name', 'city', 'country', 'is_active')
    show_change_link = True


class SiteSettingsInline(admin.StackedInline):
    model = SiteSettings
    can_delete = False
    fieldsets = (
        ('Company', {
            'fields': ('company_name', 'developer_name', 'developer_phone'),
        }),
        ('Contact', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number'),
        }),
        ('Stripe', {
            'classes': ('collapse',),
            'fields': ('stripe_enabled', 'stripe_public_key', 'stripe_secret_key'),
        }),
        ('Social Media', {
            'classes': ('collapse',),
            'fields': ('social_facebook', 'social_instagram', 'social_twitter', 'social_tiktok'),
        }),
        ('Analytics', {
            'classes': ('collapse',),
            'fields': ('google_analytics_id',),
        }),
    )


class DestinationInline(admin.TabularInline):
    model = Destination
    extra = 0
    fields = ('name', 'destination_type', 'address', 'is_active')
    show_change_link = True


class AirportCategoryPriceInline(admin.TabularInline):
    model = AirportCategoryPrice
    extra = 0
    fields = ('vehicle_category', 'base_price', 'base_km', 'price_per_km', 'is_active')
    show_change_link = True


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0
    fields = ('name', 'model_year', 'price_multiplier', 'is_active')
    show_change_link = True


# ──────────────────────────────────────────────
#  Site
# ──────────────────────────────────────────────

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'domain', 'default_language', 'is_active', 'color_preview')
    list_filter = ('is_active', 'default_language')
    search_fields = ('name', 'slug', 'domain')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SiteSettingsInline, AirportInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'domain', 'tagline', 'is_active', 'default_language'),
        }),
        ('Hero Section', {
            'fields': ('hero_title', 'hero_subtitle', 'hero_video_url'),
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color', 'secondary_color'),
        }),
    )

    @admin.display(description='Colors')
    def color_preview(self, obj):
        return format_html(
            '<span style="background:{}; padding: 2px 12px; margin-right:4px; border:1px solid #ccc;">&nbsp;</span>'
            '<span style="background:{}; padding: 2px 12px; border:1px solid #ccc;">&nbsp;</span>',
            obj.primary_color,
            obj.secondary_color,
        )


# ──────────────────────────────────────────────
#  Airport
# ──────────────────────────────────────────────

@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city', 'country', 'site', 'is_active')
    list_filter = ('site', 'country', 'is_active')
    search_fields = ('name', 'code', 'city')
    list_select_related = ('site',)
    inlines = [DestinationInline, AirportCategoryPriceInline]

    fieldsets = (
        (None, {
            'fields': ('site', 'name', 'code', 'city', 'country', 'is_active'),
        }),
        ('Details', {
            'fields': ('description', 'image'),
        }),
        ('Geolocation', {
            'classes': ('collapse',),
            'fields': ('latitude', 'longitude'),
        }),
    )


# ──────────────────────────────────────────────
#  Destination
# ──────────────────────────────────────────────

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'airport', 'destination_type', 'is_active')
    list_filter = ('airport__site', 'destination_type', 'is_active')
    search_fields = ('name', 'address', 'airport__name', 'airport__code')
    list_select_related = ('airport', 'airport__site')

    fieldsets = (
        (None, {
            'fields': ('airport', 'name', 'destination_type', 'address', 'is_active'),
        }),
        ('Media & Description', {
            'fields': ('description', 'image'),
        }),
        ('Geolocation', {
            'classes': ('collapse',),
            'fields': ('latitude', 'longitude'),
        }),
    )


# ──────────────────────────────────────────────
#  Pricing Rule
# ──────────────────────────────────────────────

@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ('site', 'service_type', 'vehicle_display', 'vehicle_category', 'base_price', 'price_per_km', 'km_threshold', 'is_active')
    list_filter = ('site', 'service_type', 'vehicle_category', 'is_active')
    search_fields = ('vehicle__name', 'vehicle_category__name')
    list_select_related = ('site', 'vehicle', 'vehicle_category')

    fieldsets = (
        ('Service', {
            'fields': ('site', 'service_type', 'vehicle', 'vehicle_category'),
        }),
        ('Pricing', {
            'fields': ('base_price', 'price_per_km', 'km_threshold', 'minimum_price'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )

    @admin.display(description='Vehicle')
    def vehicle_display(self, obj):
        return obj.vehicle.name if obj.vehicle else '—'


@admin.register(AirportCategoryPrice)
class AirportCategoryPriceAdmin(admin.ModelAdmin):
    list_display = ('airport', 'vehicle_category', 'base_price', 'base_km', 'price_per_km', 'is_active')
    list_filter = ('airport__site', 'airport', 'is_active')
    search_fields = ('vehicle_category__name', 'airport__code')
    list_select_related = ('airport', 'vehicle_category', 'airport__site')


# ──────────────────────────────────────────────
#  Vehicle Category & Vehicle
# ──────────────────────────────────────────────

@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'passengers_capacity', 'luggage_capacity', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [VehicleInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active', 'order'),
        }),
        ('Capacity', {
            'fields': ('passengers_capacity', 'luggage_capacity'),
        }),
        ('Media', {
            'fields': ('image', 'spline_scene_url'),
        }),
    )


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'model_year', 'price_multiplier', 'is_active')
    list_filter = ('category', 'sites', 'is_active')
    search_fields = ('name',)
    list_select_related = ('category',)
    filter_horizontal = ('sites',)

    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'model_year', 'is_active'),
        }),
        ('Availability', {
            'fields': ('sites',),
        }),
        ('Pricing & Features', {
            'fields': ('price_multiplier', 'features'),
        }),
        ('Media', {
            'fields': ('image',),
        }),
    )


# ──────────────────────────────────────────────
#  Premium Add-On
# ──────────────────────────────────────────────

@admin.register(PremiumAddOn)
class PremiumAddOnAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'icon', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'price', 'icon', 'is_active'),
        }),
    )


# ──────────────────────────────────────────────
#  Booking
# ──────────────────────────────────────────────

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference', 'customer_name', 'service_type', 'status',
        'pickup_date', 'total_price', 'payment_status', 'booking_source', 'site',
    )
    list_filter = ('site', 'status', 'service_type', 'payment_status', 'booking_source', 'pickup_date')
    search_fields = ('booking_reference', 'customer_name', 'customer_email', 'customer_phone', 'flight_number')
    list_select_related = ('site', 'airport', 'destination', 'vehicle', 'vehicle_category')
    readonly_fields = ('booking_reference', 'created_at', 'updated_at')
    filter_horizontal = ('addons',)
    date_hierarchy = 'pickup_date'

    fieldsets = (
        ('Booking Info', {
            'fields': ('site', 'booking_reference', 'service_type', 'status'),
        }),
        ('Customer', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_whatsapp'),
        }),
        ('Trip Details', {
            'fields': (
                'airport', 'destination', 'pickup_address', 'dropoff_address',
                'pickup_date', 'pickup_time', 'flight_number',
            ),
        }),
        ('Hourly Service', {
            'classes': ('collapse',),
            'fields': ('hours_requested', 'hourly_rate'),
        }),
        ('Vehicle & Add-Ons', {
            'fields': ('vehicle', 'vehicle_category', 'addons'),
        }),
        ('Pricing', {
            'fields': ('base_price', 'addons_total', 'platform_fee', 'total_price', 'currency'),
        }),
        ('Platform', {
            'fields': ('booking_source', 'platform_commission_rate'),
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'stripe_payment_id'),
        }),
        ('Notes', {
            'classes': ('collapse',),
            'fields': ('customer_notes', 'internal_notes', 'driver_notes'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Recalculate totals when saving via admin.
        Automatically sends email + WhatsApp notifications on status changes.
        """
        # Capture old status before save
        old_status = None
        if obj.pk:
            try:
                old_status = Booking.objects.get(pk=obj.pk).status
            except Booking.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)
        # Recalculate after save so M2M addons are committed
        obj.calculate_total()
        obj.save()

        # ── Send notifications on status changes ──
        new_status = obj.status
        if old_status != new_status:
            from core.emails import send_booking_email
            from core.whatsapp import send_whatsapp

            # Map Booking status -> email_type
            status_to_type = {
                'PENDING': 'processing',
                'CONFIRMED': 'confirmed',
                'COMPLETED': 'completed',
                'CANCELLED': 'cancelled',
            }

            email_type = status_to_type.get(new_status)
            if email_type:
                try:
                    send_booking_email(obj, email_type)
                    self.message_user(
                        request,
                        f'Email "{email_type}" sent to {obj.customer_email}.',
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f'Email "{email_type}" failed: {str(e)}',
                        level='WARNING',
                    )

                try:
                    send_whatsapp(obj, email_type)
                except Exception as e:
                    self.message_user(
                        request,
                        f'WhatsApp notification failed: {str(e)}',
                        level='WARNING',
                    )
# ──────────────────────────────────────────────
#  Site Content (CMS)
# ──────────────────────────────────────────────

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ('key', 'label', 'site', 'category', 'language', 'order')
    list_filter = ('site', 'category', 'language')
    search_fields = ('key', 'label', 'value')
    list_select_related = ('site',)
    list_editable = ('order',)

    fieldsets = (
        (None, {
            'fields': ('site', 'key', 'label', 'category', 'language', 'order'),
        }),
        ('Content', {
            'fields': ('value', 'image'),
        }),
    )


# ──────────────────────────────────────────────
#  Testimonial
# ──────────────────────────────────────────────

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'rating_stars', 'service_type', 'site', 'is_featured', 'created_at')
    list_filter = ('site', 'rating', 'service_type', 'is_featured')
    search_fields = ('customer_name', 'comment')
    list_select_related = ('site',)

    fieldsets = (
        (None, {
            'fields': ('site', 'customer_name', 'rating', 'comment', 'service_type', 'is_featured'),
        }),
    )

    @admin.display(description='Rating')
    def rating_stars(self, obj):
        return '⭐' * obj.rating


# ──────────────────────────────────────────────
#  Site Settings (standalone — also inlined on Site)
# ──────────────────────────────────────────────

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site', 'company_name', 'stripe_enabled', 'contact_email')
    list_filter = ('stripe_enabled',)
    list_select_related = ('site',)

    fieldsets = (
        ('Company', {
            'fields': ('site', 'company_name', 'developer_name', 'developer_phone'),
        }),
        ('Contact', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number'),
        }),
        ('Stripe', {
            'fields': ('stripe_enabled', 'stripe_public_key', 'stripe_secret_key'),
        }),
        ('Social Media', {
            'fields': ('social_facebook', 'social_instagram', 'social_twitter', 'social_tiktok'),
        }),
        ('Analytics', {
            'fields': ('google_analytics_id',),
        }),
    )


# ──────────────────────────────────────────────
#  Profit Report
# ──────────────────────────────────────────────

@admin.register(ProfitReport)
class ProfitReportAdmin(admin.ModelAdmin):
    list_display = (
        'site', 'month', 'year', 'total_bookings',
        'total_revenue', 'platform_fees', 'net_revenue', 'expenses', 'profit',
    )
    list_filter = ('site', 'year')
    list_select_related = ('site',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Period', {
            'fields': ('site', 'month', 'year'),
        }),
        ('Revenue', {
            'fields': ('total_bookings', 'total_revenue', 'platform_fees', 'net_revenue'),
        }),
        ('Expenses & Profit', {
            'fields': ('expenses', 'profit'),
        }),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at',),
        }),
    )


# ──────────────────────────────────────────────
#  Booking Payment
# ──────────────────────────────────────────────

@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'payment_date', 'payment_method')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('booking__booking_reference', 'booking__customer_name', 'notes')


# ──────────────────────────────────────────────
#  Email Template
# ──────────────────────────────────────────────

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('site', 'email_type', 'subject')
    list_filter = ('site', 'email_type')
    search_fields = ('subject', 'html_content', 'text_content')
