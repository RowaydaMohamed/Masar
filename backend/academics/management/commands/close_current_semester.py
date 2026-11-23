from django.core.management.base import BaseCommand
from academics.services import close_semester, DomainError
from academics.models import Semester

class Command(BaseCommand):
    help = "يغلق الترم الدراسي الحالي ويسجل لقطات سجل الطلاب ويرقي المستويات."

    def handle(self, *args, **kwargs):
        current = Semester.objects.filter(is_current=True).first()
        if not current:
            self.stdout.write(self.style.ERROR("لا يوجد ترم حالي."))
            return
            
        try:
            close_semester(current)
            self.stdout.write(self.style.SUCCESS(f"تم بنجاح إغلاق الترم: {current.label}"))
        except DomainError as e:
            self.stdout.write(self.style.ERROR(f"فشل الإغلاق: {str(e)}"))