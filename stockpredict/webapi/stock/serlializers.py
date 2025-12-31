from django.db.models import fields
from rest_framework import serializers
from .models import Company
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('company_id','exchange','shortName','industryID','industryIDv2',
                  'industry','industryEn','establishedYear','noEmployees','noShareholders',
                  'foreignPercent','website','deltaInWeek','deltaInMonth','deltaInYear',
                  'outstandingShare','issueShare','companyType','ticker')