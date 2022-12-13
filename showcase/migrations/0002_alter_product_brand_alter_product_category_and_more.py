# Generated by Django 4.1.3 on 2022-11-29 21:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('showcase', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='showcase.brand'),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='showcase.category'),
        ),
        migrations.AlterField(
            model_name='product',
            name='distributor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='showcase.distributor'),
        ),
        migrations.AlterField(
            model_name='product',
            name='manufacturer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='showcase.manufacturer'),
        ),
        migrations.AlterField(
            model_name='product',
            name='msrp',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='release_date',
            field=models.DateField(null=True),
        ),
    ]