from django.shortcuts import render

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import HttpResponse

import json

from .models import User


def hello_world(request):
    return HttpResponse("Hello, AI Server!")

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@csrf_exempt
def register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            avatar_url = data.get('avatarUrl')

            if not username or not password or not avatar_url:
                return JsonResponse({'error': '请提供完整信息'}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': '用户名已存在'}, status=400)

            # 保存用户信息到数据库
            user = User.objects.create(username=username, password=password, avatar_url=avatar_url)
            # 生成 JWT Token
            tokens = get_tokens_for_user(user)

            #userId = user.id

            #User.objects.update(userId=userId)
            user.userId = user.id
            user.save()  # 只保存当前行的 userId
            # 返回 userId 和 JWT Token
            return JsonResponse({
                'message': '注册成功',
                'userId': user.userId,
                'token': tokens['access'],  # 返回 access token
                'refresh': tokens['refresh']  # 返回 refresh token
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': '请求数据格式错误'}, status=400)

    return JsonResponse({'error': '无效的请求方法'}, status=405)



# 生成 JWT Token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return JsonResponse({'error': '用户名和密码不能为空'}, status=400)

        # 验证用户名和密码
        try:

            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'error': '用户名不存在'}, status=400)
        #user = authenticate(username=username, password=password)
        if password==user.password:
            tokens = get_tokens_for_user(user)  # 生成 JWT Token
            return JsonResponse({
                'message': '登录成功',
                'userId': user.id,
                'token': tokens['access'],  # 返回 access token
                'refresh': tokens['refresh']  # 返回 refresh token
            }, status=200)
        else:
            return JsonResponse({'error': '用户名或密码错误'}, status=400)