from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from .models import Data, Announcement, Member
from .forms import DataForm, AnnouncementForm, MemberForm

from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.db.models import Count, Max
from django.db.models.expressions import RawSQL

#CSV import
from tablib import Dataset

# for Infinite Scroll
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def detail(request, pk):
    data = get_object_or_404(Data, pk=pk)
    username = request.COOKIES.get('username', '')
    ctx={}

    if not username:
        return redirect('loginpage')


    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user


    memberList = Member.objects.filter(data__pk=pk)

    ctx = {
        'post': data,
        'username': username,
        'memberList': memberList,
    }

    return render(request, 'detail.html', ctx)


@csrf_exempt
def csv_upload(request):
    username = request.COOKIES.get('username', '')
    ctx = {}

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
        if user.is_staff is False:
            return redirect('main')
    else:
        return redirect('loginpage')

    if request.method == 'POST':
        dataset = Dataset()
        new_usergroup = request.FILES['myfile']
        imported_data = dataset.load(new_usergroup.read().decode('euc-kr'), format='csv')

        group_no = "1"
        group_list = []
        for data in imported_data:
            if group_no == data[0]:
                group_list.append(data)

            else:
                group_list.sort(key=lambda tup: tup[1])

                is_first = 1

                for elem in group_list:
                    if is_first:
                        user_id = "group"+elem[0]
                        user_pw = elem[1]
                        user_email = elem[2]
                        is_first = 0

                    if User.objects.filter(username=user_id).exists():
                        member_student_id = elem[1]
                        member_name = elem[3]
                        member_email = elem[2]
                        Member.objects.create(user=User.objects.get(username=user_id), student_id = member_student_id, name = member_name, email = member_email)
                    else:
                        User.objects.create_user(username=user_id,
                                            email=user_email,
                                            password=user_pw)
                        member_student_id = elem[1]
                        member_name = elem[3]
                        member_email = elem[2]
                        Member.objects.create(user=User.objects.get(username=user_id), student_id = member_student_id, name = member_name, email = member_email)


                group_list.clear()
                group_no = data[0]
                group_list.append(data)


        is_first = 1

        for elem in group_list:
            if is_first:
                user_id = "group"+elem[0]
                user_pw = elem[1]
                user_email = elem[2]
                is_first = 0

            if User.objects.filter(username=user_id).exists():
                member_student_id = elem[1]
                member_name = elem[3]
                member_email = elem[2]
                Member.objects.create(user=User.objects.get(username=user_id), student_id = member_student_id, name = member_name, email = member_email)
            else:
                User.objects.create_user(username=user_id,
                                    email=user_email,
                                    password=user_pw)
                member_student_id = elem[1]
                member_name = elem[3]
                member_email = elem[2]
                Member.objects.create(user=User.objects.get(username=user_id), student_id = member_student_id, name = member_name, email = member_email)

        group_list.clear()

        messages.success(request, '계정들을 성공적으로 생성하였습니다.', extra_tags='alert')


    if username:
        ctx['username'] = username

    return render(request, 'csv_upload.html', ctx)

def photoList(request, user):
    username = request.COOKIES.get('username', '')
    picList = Data.objects.raw('SELECT * FROM photos_data WHERE author = %s ORDER BY id DESC', [user])
    if username:
        userobj = User.objects.get(username=username)
        if userobj.is_staff is False:
            return redirect('loginpage')
    else:
        return redirect('loginpage')

    ctx = {
        'list' : picList,
        'user' : user,
        'userobj' : userobj,
    }

    if username:
        ctx['username'] = username

    return render(request, 'list.html', ctx)



def userList(request):
    username = request.COOKIES.get('username', '')
    if username:
        user = User.objects.get(username=username)
        if user.is_staff is False:
            return redirect('main')
    else:
        return redirect('loginpage')

    userlist = User.objects.all().annotate(
        num_posts = Count('data'),
        recent = Max('data__date'),
    ).order_by('-num_posts')

    ctx = {
        'list' : userlist,
        'userobj' : user,
    }
    if username:
        ctx['username'] = username

    return render(request, 'userlist.html', ctx)


def announce(request):
    username = request.COOKIES.get('username', '')

    ctx={}
    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
        ctx['username'] = username
    else:
        return redirect('loginpage')

    announceList = Announcement.objects.all()
    ctx['list'] = announceList

    return render(request, 'announce.html', ctx)


def main(request):
    username  = request.COOKIES.get('username', '')
    ctx={}

    if username:
        ctx['username'] = username
    else:
        return redirect('loginpage')

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
        if user.is_staff is True:
            return redirect('userList')
    else:
        return redirect('loginpage')

    if request.method == "GET":
        form = DataForm(user=request.user)
    elif request.method == "POST":
        form = DataForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            obj = form.save()
            obj.user = user
            obj.author = username

            num = user.userinfo.num_posts
            user.userinfo.num_posts = num + 1
            user.userinfo.most_recent = obj.date
            user.userinfo.name = username
            user.save()

            obj.save()
            messages.success(request, '게시물을 등록하였습니다.', extra_tags='alert')
            return HttpResponseRedirect(reverse('main'))


    dataList = Data.objects.raw('SELECT * FROM photos_data WHERE author = %s ORDER BY id DESC', [username])

    paginator = Paginator(dataList, 4)
    page = request.GET.get('page', 1)

    try:
        pics = paginator.page(page)
    except PageNotAnInteger:
        pics = paginator.page(1)
    except EmptyPage:
        pics = paginator.page(paginator.num_pages)

    ctx['form'] = form
    ctx['pics'] = pics
    ctx['userobj'] = user

    return render(request, 'main.html', ctx)

def confirm_delete_data(request, pk):
    loginname = request.COOKIES.get('username', '')
    ctx={}

    if loginname:
        pass
    else:
        return redirect('loginpage')

    item = Data.objects.get(id=pk)
    username = item.author
    user = User.objects.get(username=username)

    if user.userinfo.num_posts > 0:
        user.userinfo.num_posts -= 1
        user.save()

    Data.objects.filter(id=pk).delete()
    return redirect('main')

def confirm_delete_announce(request, pk):
    loginname  = request.COOKIES.get('username', '')
    ctx={}

    if loginname:
        pass
    else:
        return redirect('loginpage')

    item = Announcement.objects.get(id=pk)
    username = item.author
    user = User.objects.get(username=username)

    Announcement.objects.filter(id=pk).delete()
    messages.success(request, '공지가 삭제되었습니다.', extra_tags='alert')
    return redirect('announce')


# User Login Customization

def loginpage(request):
    if request.method == 'POST':
        username = request.POST['username']
        password =  request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            post = User.objects.filter(username=username)

            if post:
                login(request, user)
                username = request.POST['username']
                response = HttpResponseRedirect(reverse('main'))
                response.set_cookie('username', username, 3600)
                messages.success(request, '환영합니다.', extra_tags='alert')
                return response
            else:
                messages.warning(request, '다시 로그인 해주세요.', extra_tags='alert')
                return render(request, 'login.html', {})
        else:
            messages.warning(request, '다시 로그인 해주세요.', extra_tags='alert')
    return render(request, 'login.html', {})

def profile(request):
    username = request.COOKIES.get('username', '')
    ctx={}

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
    else:
        return redirect('loginpage')

    if username:
        ctx['username'] = username

    memberList = Member.objects.filter(user=user).annotate(
        num_posts = Count('data'),
    )
    ctx['list'] = memberList

    return render(request, 'profile.html', ctx)

def logout_view(request):
    try:
        logout(request)
        response = HttpResponseRedirect(reverse('loginpage'))
        response.delete_cookie('username')
        return response
        messages.success(request, '로그아웃 되었습니다.', extra_tags='alert')
    except:
        pass
    return render(request, 'home.html', {})


def signup(request):
    username  = request.COOKIES.get('username', '')
    ctx = {}

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
        if user.is_staff is False:
            return redirect('main')
    else:
        return redirect('loginpage')

    ctx['username'] = username
    if request.method == 'POST':
        if request.POST["password1"] == request.POST["password2"]:
            user = User.objects.create_user(
                    username=request.POST["username"],
                    password=request.POST["password1"])
            messages.success(request, '유저가 성공적으로 추가되었습니다.', extra_tags='alert')
            return redirect("profile")

        else:
            messages.warning(request, '유저를 만드는데 실패하였습니다.', extra_tags='alert')
        return render(request, 'signup.html', ctx)

    return render(request, 'signup.html', ctx)

def announce_write(request):
    username  = request.COOKIES.get('username', '')
    ctx = {}
    if username:
        ctx['username'] = username
        user = User.objects.get(username = username)
        ctx['userobj'] = user
        if user.is_staff is False:
            return redirect('announce')
    else:
        return redirect('loginpage')

    if request.method == "GET":
        form = AnnouncementForm()
    elif request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            obj.author = username
            obj.save()
            messages.success(request, '공지가 추가되었습니다.', extra_tags='alert')
            return redirect("announce")

    ctx['form'] = form

    return render(request, 'announce_write.html', ctx)

def announce_detail(request, pk):
    post = get_object_or_404(Announcement, pk=pk)
    username = request.COOKIES.get('username', '')

    ctx = {
        'post': post,
    }

    if username:
        user = User.objects.get(username = username)
        ctx['userobj'] = user
        ctx['username'] = username
    else:
        return redirect('loginpage')

    return render(request, 'announce_content.html', ctx)


def change_password(request):
    username  = request.COOKIES.get('username', '')
    ctx = {}

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user
    else:
        return redirect('loginpage')

    ctx['username'] = username
    if request.method == 'POST':
        old_password = request.POST["old_password"]
        is_pw_correct = authenticate(username=username, password=old_password)
        if is_pw_correct is not None:
            password1 = request.POST["password1"]
            password2 = request.POST["password2"]

            if password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(request, '비밀번호가 변경 되었습니다.', extra_tags='alert')
                return redirect("profile")

            else:
                messages.warning(request, '바꾸는 비밀번호가 일치해야합니다.', extra_tags='alert')

            return redirect("change_password")
        else:
            messages.warning(request, '현재 비밀번호를 확인해주세요.', extra_tags='alert')
            return render(request, 'change_password.html', ctx)

    return render(request, 'change_password.html', ctx)


def add_member(request):
    username  = request.COOKIES.get('username', '')
    ctx={}

    if username:
        ctx['username'] = username
    else:
        return redirect('loginpage')

    if username:
        user = User.objects.get(username=username)
        ctx['userobj'] = user

    if request.method == "GET":
        form = MemberForm()
    elif request.method == "POST":
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            obj.author = username
            obj.user = user
            obj.save()
            messages.success(request, '멤버가 추가되었습니다.', extra_tags='alert')
            return redirect("profile")

    ctx['form'] = form

    return render(request, 'member.html', ctx)

def confirm_delete_member(request, pk):
    item = Member.objects.get(id=pk)
    Member.objects.filter(id=pk).delete()
    return redirect('profile')


def confirm_delete_user(request, pk):
    user = User.objects.get(id=pk)
    User.objects.filter(id=pk).delete()
    return redirect('userList')
