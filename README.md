# 考核评分系统
QQ：792301982

# 镜像
使用Dockerfile构建镜像 
```
docker build --network=host -t teacherscore:latest .
```

将镜像保存出来
```
docker save -o mysql.tar mysql:latest
docker save -o teacherscore.tar teacherscore:latest
```

压缩
```
tar -Jcvf mysql.tar.xz mysql.tar
tar -Jcvf teacherscore.tar.xz teacherscore.tar
```

# 离线部署
1. 在服务上安装docker和docker compose
2. 在本地电脑windows中使用 scp 命令将 docker 镜像，docker compose脚本上传到服务器
```
scp .\Desktop\mysql.tar.xz root@172.28.8.90:~/teacherscore
scp .\Desktop\teacherscore.tar.xz root@172.28.8.90:~/teacherscore
scp .\Desktop\docker-compose.yml root@172.28.8.90:~/teacherscore
```

3. 在服务器linux上解压它们
```
cd ~/teacherscore
tar -xvf mysql.tar.xz
tar -xvf teacherscore.tar.xz
```

4. 导入docker镜像
```
docker load -i mysql
docker load -i teacherscore
```

5. 使用docker compose部署
```
export DOCKER_API_VERSION=1.41
docker compose up -d
```

如果要关闭，此操作会删除mysql所有数据，使用：
```
docker compose down -v
```