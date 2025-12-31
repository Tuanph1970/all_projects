from django.db import models

# Create your models here.
class AutoPart(models.Model):
    maker = models.CharField(max_length=50)
    autoname = models.CharField(max_length=100)
    def __str__(self)->str:
        return self.maker
class Company(models.Model):

    company_id = models.IntegerField
    exchange = models.CharField(max_length=8)
    shortName = models.CharField(max_length=100)
    industryID = models.IntegerField
    industryIDv2 = models.IntegerField
    industry = models.CharField(max_length=30)
    industryEn = models.CharField(max_length=30)
    establishedYear = models.IntegerField
    noEmployees = models.IntegerField
    noShareholders = models.IntegerField
    foreignPercent = models.FloatField
    website = models.CharField(max_length=100)
    deltaInWeek = models.FloatField
    deltaInMonth = models.FloatField
    deltaInYear = models.FloatField
    outstandingShare = models.FloatField
    issueShare = models.FloatField
    companyType = models.CharField(max_length=10)
    ticker = models.CharField(max_length=20)


class TblPortfolio(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    symbol = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100)
    shares = models.DecimalField(max_digits=15, decimal_places=2)
    avg_price = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_portfolio'
        unique_together = ('user_id', 'symbol')

