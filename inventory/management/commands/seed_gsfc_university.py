from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Company, EmployeeProfile, Supplier, WarehouseLocation, Product, Transaction


class Command(BaseCommand):
    help = 'Seed GSFC University sample inventory data.'

    def handle(self, *args, **options):
        User = get_user_model()

        company, created = Company.objects.get_or_create(
            slug='gsfc-university',
            defaults={
                'name': 'GSFC University',
                'notification_email': 'admin@gsfcuniversity.edu',
                'low_stock_email_notifications': True,
                'dark_mode_enabled': False,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Company: {company.name} (created={created})'))

        admin_user, created = User.objects.get_or_create(
            username='gsfc_admin',
            defaults={
                'email': 'admin@gsfcuniversity.edu',
                'is_active': True,
                'first_name': 'GSFC',
                'last_name': 'Admin',
            },
        )
        if created:
            admin_user.set_password('gsfcadmin123')
            admin_user.save()
        self.stdout.write(self.style.SUCCESS(f'Admin user: {admin_user.username} (created={created})'))

        profile, created = EmployeeProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'company': company,
                'role': EmployeeProfile.ROLE_OWNER,
                'full_name': 'GSFC University Admin',
                'phone': '+1-555-0160',
                'job_title': 'Inventory Administrator',
                'can_manage_inventory': True,
                'can_manage_employees': True,
                'can_view_reports': True,
                'must_change_password': False,
                'email_verified': True,
                'is_active_employee': True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Employee profile: {profile.full_name} (created={created})'))

        suppliers_data = [
            {
                'name': 'Campus Tech Supplies',
                'contact_person': 'Dr. Priya Menon',
                'email': 'priya.menon@campustech.com',
                'phone': '+1-555-0201',
            },
            {
                'name': 'Library Resources Inc',
                'contact_person': 'Nikhil Sharma',
                'email': 'nikhil.sharma@libraryresources.com',
                'phone': '+1-555-0202',
            },
            {
                'name': 'Lab Equipment Solutions',
                'contact_person': 'Ayesha Khan',
                'email': 'ayesha.khan@labequip.com',
                'phone': '+1-555-0203',
            },
        ]

        suppliers = []
        for data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                company=company,
                name=data['name'],
                defaults={
                    'contact_person': data['contact_person'],
                    'email': data['email'],
                    'phone': data['phone'],
                },
            )
            suppliers.append(supplier)
            self.stdout.write(self.style.SUCCESS(f'Supplier: {supplier.name} (created={created})'))

        locations_data = [
            {
                'name': 'Main Campus Warehouse',
                'code': 'GSFC-WH',
                'location_type': WarehouseLocation.TYPE_WAREHOUSE,
            },
            {
                'name': 'Science Block Storage',
                'code': 'GSFC-SCI',
                'location_type': WarehouseLocation.TYPE_ROOM,
            },
            {
                'name': 'Library Storage',
                'code': 'GSFC-LIB',
                'location_type': WarehouseLocation.TYPE_ROOM,
            },
        ]

        locations = []
        for data in locations_data:
            location, created = WarehouseLocation.objects.get_or_create(
                company=company,
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'location_type': data['location_type'],
                    'is_default': data['code'] == 'GSFC-WH',
                },
            )
            locations.append(location)
            self.stdout.write(self.style.SUCCESS(f'Location: {location.name} (created={created})'))

        products_data = [
            {
                'name': 'Laboratory Microscope',
                'category': 'Lab Equipment',
                'sku': 'GSFC-LAB-001',
                'quantity': 10,
                'price': 1250.00,
                'reorder_level': 2,
            },
            {
                'name': 'Projector',
                'category': 'AV Equipment',
                'sku': 'GSFC-AV-001',
                'quantity': 8,
                'price': 650.00,
                'reorder_level': 1,
            },
            {
                'name': 'Graphing Calculator',
                'category': 'Academic Supplies',
                'sku': 'GSFC-AC-001',
                'quantity': 120,
                'price': 89.50,
                'reorder_level': 20,
            },
            {
                'name': 'Whiteboard Markers Set',
                'category': 'Office Supplies',
                'sku': 'GSFC-OS-001',
                'quantity': 250,
                'price': 12.00,
                'reorder_level': 50,
            },
            {
                'name': 'Ethernet Switch 24-Port',
                'category': 'Network Hardware',
                'sku': 'GSFC-NW-001',
                'quantity': 15,
                'price': 230.00,
                'reorder_level': 3,
            },
            {
                'name': '3D Printer Filament',
                'category': 'Lab Supplies',
                'sku': 'GSFC-LS-001',
                'quantity': 60,
                'price': 39.99,
                'reorder_level': 10,
            },
            {
                'name': 'Conference Room Table',
                'category': 'Furniture',
                'sku': 'GSFC-FN-001',
                'quantity': 5,
                'price': 480.00,
                'reorder_level': 1,
            },
            {
                'name': 'Study Desk Lamp',
                'category': 'Lighting',
                'sku': 'GSFC-LT-001',
                'quantity': 75,
                'price': 24.99,
                'reorder_level': 10,
            },
            {
                'name': 'External SSD 2TB',
                'category': 'IT Equipment',
                'sku': 'GSFC-IT-001',
                'quantity': 30,
                'price': 169.99,
                'reorder_level': 5,
            },
            {
                'name': 'Library Barcode Scanner',
                'category': 'Library Equipment',
                'sku': 'GSFC-LB-001',
                'quantity': 20,
                'price': 99.99,
                'reorder_level': 5,
            },
        ]

        products = []
        for index, item in enumerate(products_data):
            supplier = suppliers[index % len(suppliers)]
            location = locations[index % len(locations)]
            product, created = Product.objects.get_or_create(
                company=company,
                sku=item['sku'],
                defaults={
                    'name': item['name'],
                    'category': item['category'],
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'reorder_level': item['reorder_level'],
                    'supplier': supplier,
                    'location': location,
                    'is_active': True,
                },
            )
            products.append(product)
            self.stdout.write(self.style.SUCCESS(f'Product: {product.name} (SKU={product.sku}) (created={created})'))

        transaction_notes = [
            'Initial inventory receipt',
            'Replenished stock for semester',
            'Received department order',
            'Batch restock',
            'Lab supply replenishment',
        ]

        for i, product in enumerate(products[:5]):
            transaction, created = Transaction.objects.get_or_create(
                company=company,
                product=product,
                location=product.location,
                quantity=5 + i * 2,
                transaction_type=Transaction.STOCK_IN,
                note=transaction_notes[i],
                performed_by=admin_user,
                defaults={
                    'date': timezone.now(),
                },
            )
            if created:
                product.quantity += transaction.quantity
                product.save()
            self.stdout.write(self.style.SUCCESS(f'Transaction: {transaction.product.name} +{transaction.quantity} (created={created})'))

        self.stdout.write(self.style.SUCCESS('GSFC University sample data seeded successfully.'))
