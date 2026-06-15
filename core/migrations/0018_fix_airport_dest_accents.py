from django.db import migrations

def fix_accents(apps, schema_editor):
    Airport = apps.get_model('core', 'Airport')
    Destination = apps.get_model('core', 'Destination')
    
    airports_fixes = {
        'AZS': ('Aeropuerto Internacional de Samaná El Catey', 'Samaná'),
        'BRX': ('Aeropuerto Internacional María Montez', 'Barahona'),
        'POP': ('Aeropuerto Internacional Gregorio Luperón', 'Puerto Plata'),
        'SDQ': ('Aeropuerto Internacional Las Américas', 'Santo Domingo'),
        'PUJ': ('Aeropuerto Internacional de Punta Cana', 'Punta Cana'),
        'LRM': ('Aeropuerto Internacional La Romana', 'La Romana'),
        'STI': ('Aeropuerto Internacional del Cibao', 'Santiago de los Caballeros'),
    }
    for code, (name, city) in airports_fixes.items():
        Airport.objects.filter(code=code).update(name=name, city=city)
        
    for dest in Destination.objects.all():
        name_lower = dest.name.lower()
        # Robust matches for Bavaro / Bayahibe / Juan Dolio (Macoris)
        if 'b' in name_lower and 'v' in name_lower and 'r' in name_lower:
            dest.name = 'Bávaro — Hotel Zone'
            dest.address = 'Bávaro, Punta Cana'
            dest.save()
        elif 'bay' in name_lower or ('b' in name_lower and 'y' in name_lower and 'h' in name_lower):
            dest.name = 'Bayahíbe'
            dest.address = 'Bayahíbe, La Altagracia'
            dest.save()
        elif 'dolio' in name_lower or 'macor' in name_lower or 'maco' in name_lower or 'dol' in name_lower:
            dest.name = 'Juan Dolio'
            dest.address = 'Juan Dolio, San Pedro de Macorís'
            dest.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_alter_booking_status'),
    ]

    operations = [
        migrations.RunPython(fix_accents),
    ]
