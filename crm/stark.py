from stark.service.stark import site,ModelStark
from crm import models
from django.utils.safestring import mark_safe
from django.conf.urls import url
from django.shortcuts import HttpResponse,redirect,render
from django.http import JsonResponse

class userConfig(ModelStark):
    list_display = ['name','email','depart']

class classConfig(ModelStark):

    def class_name(self,obj=None,header=False):
        if header:
            return "课程名"
        else:
            return "{}({})".format(obj.course.name,str(obj.semester))
    list_display = [class_name,'tutor','price','teachers']

class customerConfig(ModelStark):

    def display_gender(self,obj=None,header=False):
        if header:
            return "性别"
        else:
            for key,value in obj.gender_choices:
                if key==obj.gender:
                    return value

    def dispaly_education(self,obj=None,header=False):
        if header:
            return  "学历"
        else:
            return obj.get_education_display()

    def display_course(self,obj=None,header=False):
        if header:
            return "咨询课程"
        else:
            course_list = []
            ret = obj.course.all()
            for course_obj in ret:
                course_str = "<a class='btn btn-primary btn-sm' href='customer/cancel_course/{}/{}'>{}</a>".format(obj.pk,course_obj.pk,course_obj.name)
                course_list.append(course_str)
            return mark_safe(' '.join(course_list))

    # 公共客户资源页面视图函数

    import datetime
    def public_views(self,request):
        from django.db.models import Q
        # 找出未报名、 且 三天未跟进，或者15天未成单
        import datetime
        now = datetime.datetime.now()
        day3 = datetime.timedelta(days=3)
        day15= datetime.timedelta(days=15)
        customer_list = models.Customer.objects.filter(Q(last_consult_date__lt=now-day3)|Q(recv_date__lt=now-day15),status=2)
        return render(request,"public.html",locals())

    # 扩展url中用执行取消客户关联课程的函数
    def cancel_course(self,request,customer_id,course_id):
        obj = models.Customer.objects.filter(pk=customer_id).first()
        obj.course.remove(course_id)
        return redirect(self.get_list_url())

    # 定义扩展url
    def extend_url(self):
        url_list=[]
        url_list.append(url(r'cancel_course/(\d+)/(\d+)',self.cancel_course)),
        # 定义公共客户资源页面url
        url_list.append(url(r'public/',self.public_views))
        return url_list

    list_display = ['name',display_gender,dispaly_education,'consultant',display_course]


class ConsultRecordConfig(ModelStark):

    list_display = ['customer','consultant','date','note',]

class StudentConfig(ModelStark):
    # 学生成绩页面展示
    def show_study_record_view(self,request,studentId):
        if request.is_ajax():
            sid = request.GET.get("student_id")
            cid = request.GET.get("class_id")
            # 构造出前端需要的数据格式
            data = {
               "day_list":[],
                "num_list":[],
            }
            student_record_list = models.StudyRecord.objects.filter(student=sid,course_record__class_obj=cid)
            for student_record in student_record_list:
                data["day_list"].append("day%s"%student_record.course_record.day_num)
                data["num_list"].append(student_record.score)
            return JsonResponse(data)
        else:
            student_obj = models.Student.objects.filter(pk=studentId).first()
            class_list = student_obj.class_list.all()
            return render(request,"record_study_view.html",locals())
    # 拓展一个展示学生成绩的url
    def extend_url(self):
        url_list=[]
        url_list.append(url(r'show_study_record/(\d+)/',self.show_study_record_view))
        return url_list
    # 查看成绩字段
    def show_study_record(self,obj=None,header=False):
        if header:
            return "查看成绩"
        else:
            return mark_safe("<a href='show_study_record/{}'>{}</a>".format(obj.pk,"查看成绩"))
    list_display = ['customer','class_list',show_study_record]

class studyrecordConfig(ModelStark):
    def display_record(self,obj=None,header=False):
        if header:
            return "签到记录"
        else:
            return obj.get_record_display()

    def display_score(self,obj=None,header=False):
        if header:
            return "表现记录"
        else:
            return obj.get_score_display()

    def patch_dianming(self,request,queryset):
        queryset.update(record='late')
    list_display = ['course_record','student','record','score']
    patch_dianming.short_description = "批量改为迟到"
    actions = [patch_dianming]


class CourseRecordConfig(ModelStark):

    def record(self,obj=None,header=False):
        if header:
            return "学生记录"
        else:
            return mark_safe("<a href='/stark/crm/studyrecord/?course_record={}'>学生记录".format(obj.pk))

    def record_score_view(self,request,pk):
        if request.method == "POST":
            data_dic = {}
            for key,value in request.POST.items():
                if key == "csrfmiddlewaretoken":
                    continue
                field,id = key.rsplit("_",1)
                if id in data_dic:
                    data_dic[id][field]=value
                else:
                    data_dic[id]={field:value}
            for id,value in data_dic.items():
                models.StudyRecord.objects.filter(pk=id).update(**value)
            return redirect(request.path)
        else:
            study_record_list = models.StudyRecord.objects.filter(course_record=pk)
        return render(request,"record_score.html",locals())

    # 定义扩展url
    def extend_url(self):
        url_list=[]
        url_list.append(url(r'record_score/(\d+)/',self.record_score_view))
        return url_list

    # 录入成绩
    def record_score(self,obj=None,header=False):
        if header:
            return "录入成绩"
        else:
            return mark_safe("<a href='record_score/{}'>录入成绩</a>".format(obj.pk))

    def patch_studyrecord(self,request,queryset):
        for course_record in queryset:
            # 与course_record 关联的班级对应的所有学生
            student_list = models.Student.objects.filter(class_list__id=course_record.class_obj.pk)
            for student_obj in student_list:
                obj = models.StudyRecord.objects.create(course_record=course_record,student=student_obj)
    list_display = ['class_obj','day_num','teacher',record,record_score]
    patch_studyrecord.short_description = '批量生成学生记录'
    actions = [patch_studyrecord]

site.register(models.Department)
site.register(models.UserInfo,userConfig)
site.register(models.Student,StudentConfig)
site.register(models.ClassList,classConfig)
site.register(models.ConsultRecord,ConsultRecordConfig)
site.register(models.Customer,customerConfig)
site.register(models.Department)
site.register(models.School)
site.register(models.StudyRecord,studyrecordConfig)
site.register(models.Course)
site.register(models.CourseRecord,CourseRecordConfig)