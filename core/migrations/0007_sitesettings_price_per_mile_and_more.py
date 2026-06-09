# Generated manually for address-based airport transfer pricing

import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_booking_service_type_and_more'),
    ]

    operations = [
        # SiteSettings: price_per_mile
        migrations.AddField(
            model_name='sitesettings',
            name='price_per_mile',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('3.50'),
                help_text='Rate per mile for airport transfer distance-based pricing.',
                max_digits=6,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
            ),
        ),
        # SiteSettings: airport_base_fee
        migrations.AddField(
            model_name='sitesettings',
            name='airport_base_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('15.00'),
                help_text='Base pickup/dropoff fee added to every airport transfer.',
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
            ),
        ),
        # PricingRule: zone_min_distance_km
        migrations.AddField(
            model_name='pricingrule',
            name='zone_min_distance_km',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Minimum distance in km for this fixed-price zone.',
                null=True,
            ),
        ),
        # PricingRule: zone_max_distance_km
        migrations.AddField(
            model_name='pricingrule',
            name='zone_max_distance_km',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Maximum distance in km for this fixed-price zone.',
                null=True,
            ),
        ),
    ]
