#coding:utf-8
from django.shortcuts import render,render_to_response
from django.http import HttpResponse,HttpResponseRedirect
from django.template.loader import render_to_string
from django import forms
from models import *
from code import *
import MySQLdb
import random,time,re,sys
from django.core.cache import cache
# Create your views here.

reload(sys)
sys.setdefaultencoding('utf-8')

#连接本地数据库
conn=MySQLdb.connect(host='localhost',user='xxxx',passwd='yyyy',db='question_bank',port=3306)
cur=conn.cursor()

#生成随机服务器密钥，每次启动都不一样
key = 'a'*16
IV = 'b'*16

class Papers(object):
    def __init__(self,student_id):
        self.student_id = student_id
        self.context = {}
        self.answer = {}
        self.post_answer = {}
        self.got_score = {}
        self.start_exam_time = time.strftime("%m/%d/%Y %H:%M:%S",time.localtime(time.time()))
        self.stop_exam_time = self.start_exam_time[:-8] + '%02d'%((int(self.start_exam_time[-8:-6])+2)%24) +self.start_exam_time[-6:]

    def get_stem(self,stem_type,stem_amount):
        #获取所有stem_type的id
        cur.execute("select id from examination_problems where stem_type='%s'"%stem_type)
        query_result = cur.fetchall()    
        single_id = [int(i[0]) for i in query_result]
        #随机选取5个不重复的id
        single_choice_id = set()
        while 1:
            single_choice_id.add(random.choice(single_id))
            if len(single_choice_id)==stem_amount:
                break
        #将被随机选中的题目记录完整提取并装进context字典
        cur.execute("select * from examination_problems where id in "+str(tuple(single_choice_id)))
        query_result = cur.fetchall()    
        for item in query_result:
                #item[0]为id
                #item[1]为题目类型
                #item[2]为难度值
                #item[3]为题目
                #item[4]为选项,但对于填空和程序题，该字段为空
                #item[5]为答案,对于单选、多选、对错，该字段为正确答案的序号（从1开始）
                #对于填空、程序题，该字段为唯一的正确答案字符串
            if item[1]!='Fill in the blanks' and item[1]!='Program question':
                self.context[stem_type.split(' ')[0]+str(query_result.index(item)+1)] = {'stem':item[3],'options':item[4].split(';')}
                self.answer[stem_type.split(' ')[0]+str(query_result.index(item)+1)] = item[5]
            else:            
                self.context[stem_type.split(' ')[0]+str(query_result.index(item)+1)] = {'stem':item[3]}
                self.answer[stem_type.split(' ')[0]+str(query_result.index(item)+1)] = item[5]
    def distribute_paper(self):
        self.get_stem('Single choice',10)
        self.get_stem('Multiple choice',5)
        self.get_stem('True or false', 4)
        self.get_stem('Fill in the blanks', 4)
        self.get_stem('Program question', 2)
        self.context['stop_exam_time'] = self.stop_exam_time
        return self.context

#定义注册、登陆表单，包含提交数据的合法性验证及错误信息
class UserForm(forms.Form):
    student_id = forms.CharField(max_length=11)
    password = forms.CharField(widget=forms.PasswordInput())

    #定义注册信息中student_id字段的有效性验证函数，该字段只能是数字
    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        letter = '0123456789'
        for i in student_id:
            if i not in letter:
                raise forms.ValidationError("student id error!")
        else:
            return student_id
    #定义注册信息中password字段的有效性验证函数，该字段长度不能超过20个字符
    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password)!=64:
            raise forms.ValidationError("password length error!")
        else:
            return password

def register(request):
    context = {}
    current_ip = request.META['REMOTE_ADDR']
    if request.method == "POST":
        uf = UserForm(request.POST)
        if uf.is_valid():
            #注册提交信息合法，获取具体数据
            student_id = uf.cleaned_data['student_id']
            password = uf.cleaned_data['password']            
            #定义重定向时的安全参数.与login()配合,只有经本处重定向到login.html,且用户身份未变时才会有提示信息
            redirect_args = aes_cbc_encrypt(randbytes(16)+';'+current_ip,key,IV).encode('hex')
            try:
                #检查该student_id是否已经注册.若已经注册，则重定向到登陆页面
                User.objects.get(student_id=student_id)
                #最后一位为0表明，若身份验证通过则提示是账号已注册              
                response = HttpResponseRedirect('/login/?asi='+redirect_args+'0')                
                return response
            except User.DoesNotExist:
                User.objects.create(student_id=student_id,password=password,ip=current_ip,score=-1)
                #最后一位为1表明，若身份验证通过则提示是账号注册成功
                response = HttpResponseRedirect('/login/?asi='+redirect_args+'1')
                return response
        else:
            context['points_info'] = uf.errors.values
    else:
        context['points_info']=["Please register first ! And then login !","student id is pure digital less than 11 chars !"]
        arg = request.GET.get('reg','')
        if arg and (aes_cbc_decrypt(arg.decode('hex'),key,IV).split(';')[-1]) == current_ip:
            context['points_info']=["student id doest't exist.please register first!"] 
    context['behaviour'] = "Register"
    return render(request,'base.html',context)

def login(request):
    context = {}
    current_ip = request.META['REMOTE_ADDR']
    if request.method == 'POST':        
        uf = UserForm(request.POST)
        if uf.is_valid():
            #表单数据通过验证,获取表单数据
            student_id = uf.cleaned_data['student_id']
            password = uf.cleaned_data['password']
            ###########login_ip = request.META['REMOTE_ADDR']
            #检查是否携带token，即检测从考试页面index获取token后又尝试重新登陆的行为    
            cookie_token = request.COOKIES.get('token')
            if cookie_token:
                #考虑学生15的做题页面cookies被学生14获取，14恰好又知道15的学号和密码，此时14可以完全冒充15去答题并提交
                #所以需要验证该token携带的ip地址信息是否和当前访问者一致，以及携带的学号信息和登陆学号是否一致，以防重放攻击
                token = aes_cbc_decrypt(cookie_token.decode('hex'), key, IV)
                token_student_id = token.split(';')[0]
                token_ip = token.split(';')[-1]
                ###########if (token_ip == login_ip) and (token_student_id == student_id):
                if token_student_id == student_id:
                    #学生正尝试重新登陆，则给其返回和之前分发的相同页面
                    exec("S_"+student_id+"=cache.get('"+"S_"+student_id+"')")
                    exec('context='+'S_'+student_id+'.context')
                    context['student_id'] = student_id
                    response  = render_to_response('index.html', context)
                    return response
                else:
                    context['points_info']=["please don't hack me or cheat me!"]
                    #函数末尾填充behaviour，此处无需返回
            else:
                #学生正在进行第一次正常登陆
                #或者已经提交试卷，token置空后企图再次登陆
                try:
                    #表单数据与数据库进行比较
                    user_info = User.objects.get(student_id=student_id)
                    contrast_passwd = (user_info.password==password)
                    #对比注册时ip和当前登陆ip是否一致
                    ###########contrast_ip = (user_info.ip == request.META['REMOTE_ADDR'])
                    if user_info.score != -1:
                        context['points_info'] = ['You has submitted paper! please leave!']
                    else:                        
                        ###########if contrast_passwd and contrast_ip:
                        if contrast_passwd:
                            #比较成功，跳转index
                            response = HttpResponseRedirect('/index/')
                            #将加密的认证参数写入浏览器cookie,失效时间为60s*120=2h
                            token_arg = student_id+';'+randbytes(5)+';'+current_ip
                            token = aes_cbc_encrypt(token_arg,key,IV).encode('hex')
                            response.set_cookie('token',token,20)
                            return response
                        else:
                            #比较失败，还在login
                            if not contrast_passwd:
                                context['points_info']=['password error !']
                            ###########if not contrast_ip:
                                ###########context['points_info']=["please don't hack me or cheat me!"]
                except User.DoesNotExist:
                    response = HttpResponseRedirect('/register/?reg='+aes_cbc_encrypt(randbytes(16)+';'+current_ip,key,IV).encode('hex'))
                    return response
        else:
            context['points_info'] = uf.errors.values
    else:
        arg = request.GET.get('asi','')
        if arg:
            #验证跳转来此页面的用户地址身份，区别于直接通过url进入此页面的用户，给出提示信息
            if (aes_cbc_decrypt(arg[:-1].decode('hex'),key,IV).split(';')[-1]) == current_ip and (arg[-1] == '0'):
                context['points_info'] = ['Account has been registered ! please login !']
            if (aes_cbc_decrypt(arg[:-1].decode('hex'),key,IV).split(';')[-1]) == current_ip and (arg[-1] == '1'):
                context['points_info'] = ['Register succeed ! please login and start answing !']
    context['behaviour'] = "Login"
    return render(request, 'base.html',context)

def index(request):
    context = {}
    cookie_token = request.COOKIES.get('token')
    if cookie_token:
        token = aes_cbc_decrypt(cookie_token.decode('hex'), key, IV)
        if token=='':
            context = {'warning_info':'Please login first using your student id and password!'}
            return render(request, 'warning.html',context)
        try:
            student_id = token.split(';')[0]
            login_ip = token.split(';')[-1]
        except:
            context = {'warning_info':'Please login first using your student id and password!'}
            return render(request, 'warning.html',context)
        
        is_distributed = 'distributed' in token
        #token中包含的ip为用户注册时的ip，再跟当前登陆ip进行对比，以防重放攻击
        ###########if  login_ip == request.META['REMOTE_ADDR']:

        if not is_distributed:
            retry = 0
            while retry<1000:
                try:
                    #还没给学生组装试卷，进行该操作,并通过在token中设置字段来标识该学生的试卷已经组装过,后续不再进行组装，直到cooies过期即考试结束
                    exec('S_'+student_id+'=Papers('+"'"+student_id+"'"+')')
                    exec('context='+'S_'+student_id+'.distribute_paper()')
                    context['student_id'] = student_id
                    #将Paper实例对象进行本地内存缓存,cache.set(key,value,timeout)
                    exec("cache.set('S_"+student_id+"',"+"S_"+student_id+",60*125)")
                    #在cookie中标识已经给学生分发了试卷
                    token_arg = student_id+';'+randbytes(5)+'distributed'+';'+login_ip
                    token = aes_cbc_encrypt(token_arg,key,IV).encode('hex')
                    #组装页面,设置cookie
                    response  = render_to_response('index.html', context)
                    response.set_cookie('token',token,60*121)
                    return response
                except:
                    retry += 1
                else:
                    break
            else:
                context = {'warning_info':'something wrong happened!please F5 to reflush!'}
                return render(request, 'warning.html',context)        
        else:
            retry = 0
            while retry<1000:
                try:
                    #已经给学生组装好试卷，不再重新组装,应对学生可能无聊得刷新、重载页面的操作
                    exec("S_"+student_id+"=cache.get('"+"S_"+student_id+"')")
                    exec('context='+'S_'+student_id+'.context')
                    context['student_id'] = student_id
                    response  = render_to_response('index.html', context)
                    return response
                except:
                    retry += 1
                else:
                    break
            else:
                context = {'warning_info':'something wrong happened!please F5 to reflush!'}
                return render(request, 'warning.html',context)
    else:
        context = {'warning_info':'Please login first using your student id and password!'}
        return render(request, 'warning.html',context)

stem_id = ['Single1','Single2','Single3','Single4','Single5',
                    'Single6','Single7','Single8','Single9','Single10',
                    'Multiple1','Multiple2','Multiple3','Multiple4','Multiple5',
                    'True1','True2','True3','True4',
                    'Fill1','Fill2','Fill3','Fill4',
                    'Program1','Program2']
                    
score_calc = {'Single':2,'Multiple':4,'True':3,'Fill':4,'Program':16}

def result(request):    
    if request.method == "POST":
        post_data = request.POST
        global stem_id
        student_id = post_data['student_id']
        
        retry = 0
        while retry<100:
            try:
                exec("S_"+student_id+"=cache.get('"+"S_"+student_id+"')")
                exec('correct_answer='+'S_'+student_id+'.answer')
            except:
                retry += 1
            else:
                break
        else:
            context = {'warning_info':'something wrong happened!please F5 to reflush!'}
            return render(request, 'warning.html',context)

    	score = 0
    	for i in stem_id:
            post_answer = post_data[i].strip()
            exec("S_"+student_id+".post_answer['"+i+"']="+"post_answer")            
            if post_answer == unicode(correct_answer[i]):
                exec("S_"+student_id+".got_score['"+i+"']="+"1")
                score += score_calc[re.search(r'\D+',i).group(0)]
            else:
                exec("S_"+student_id+".got_score['"+i+"']="+"0")

        retry = 0
        while retry<100:
            try:
                user_info = User.objects.get(student_id=student_id)
                user_info.score = score
                user_info.save()
                exec("cache.set('S_"+student_id+"',"+"S_"+student_id+")")
            except:
                retry += 1
            else:
                break
        else:
            context = {'warning_info':'something wrong happened!please F5 to reflush!'}
            return render(request, 'warning.html',context)
        
        return HttpResponse('OK!')
    else:
        return HttpResponse('')
        

def score(request,student_id):
    context = {}
    cookie_token = request.COOKIES.get('token')
    if cookie_token:
        
        token = aes_cbc_decrypt(cookie_token.decode('hex'), key, IV)
        
        if token=='':
            context = {'warning_info':'something wrong happened!please F5 to reflush!'}
            return render(request, 'warning.html',context)
        
        retry = 0
        while retry<100:            
            try:
                student_id = token.split(';')[0]
                user_info = User.objects.get(student_id=student_id)
                exec("S_"+student_id+"=cache.get('"+"S_"+student_id+"')")
                exec('context='+'S_'+student_id+'.context')
                exec('post_answer='+'S_'+student_id+'.post_answer')
                exec('correct_answer='+'S_'+student_id+'.answer')
                exec('got_score='+'S_'+student_id+'.got_score')
            except:
                retry += 1
            else:
                break
        else:
            context = {'warning_info':'something wrong happened!please F5 to reflush!'}
            return render(request, 'warning.html',context)
                        
        score = user_info.score

    	if score != -1:
            context['score'] = score
            context['student_id'] = student_id
            context['post_answer'] = post_answer
            context['correct_answer'] = correct_answer
            context['got_score'] = got_score
            response  = render_to_response('score.html', context)
            response.set_cookie('token','',5)

            content = render_to_string('score.html',context)
            with open('/root/exam_system/examination/templates/exams_results/'+student_id+'.html','w') as f:
                f.write(content)

            return response
    	else:
    		context = {'warning_info':'Please go to /index again and ensure that you have finished your paper!'}
    		return render(request, 'warning.html',context)
    else:
        if student_id !="":

            try:
                user_info = User.objects.get(student_id=student_id)
            except:
                context = {'warning_info':'Examination has finished! you can close browser and leave!'}
                return render(request, 'warning.html',context)

            if user_info.score != -1:
                return render(request,'exams_results/'+student_id+'.html')
            else:
                context = {'warning_info':'The student has not submitted paper!'}
                return render(request, 'warning.html',context)
        else:
            context = {'warning_info':'Examination has finished! you can close browser and leave!'}
            return render(request, 'warning.html',context)

def warning(request):
    return render(request, 'warning.html')
