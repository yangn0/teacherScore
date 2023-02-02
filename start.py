from flask import Flask, request, jsonify
from flask import render_template
from flask import redirect, render_template, session, send_file, send_from_directory
from functools import wraps
import json,random
import mysql
import time
import os
import excel
from werkzeug.utils import secure_filename
import traceback
import statistics

app = Flask(__name__)
app.config['SECRET_KEY'] =  "yangning" # os.urandom(24)设置一个随机24位字符串为加密盐
app.config.update(TEMPLATE_AUTO_RELOAD=True)

# 装饰器装饰多个视图函数
# 登录校验
def wrapper(func):
    @wraps(func)  # 保存原来函数的所有属性,包括文件名
    def inner(*args, **kwargs):
        # 校验session
        if session.get("user"):
            ret = func(*args, **kwargs)  # func = home
            return ret
        else:
            return redirect("/login")
    return inner

#跳转到登录
@app.route('/', methods=['GET'])
def test():
    return render_template('login.html')

#登录接口
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    t_id = request.form['t_id']
    password = request.form['password']
    s = mysql.Sql()
    r = s.search('''
        SELECT * FROM TEACHER WHERE t_id='%s' and t_password='%s'
    ''' % (t_id, password))
    if(len(r) == 0):
        return "工号或密码错误"
    if r[0]['t_id']=="anonymous":
        r[0]['t_id']="anonymous"+str(random.random())

    session["user"] = r[0]
    # 判断是否是管理员-->接入管理员端
    if(r[0]['kind'] == 0):
        return redirect("/addTeacher")
    return redirect("/index")

# 管理员修改密码接口
@app.route('/changePwd', methods=['GET', 'POST'])
@wrapper
def changePwd():
    if(request.method == "GET"):
        return render_template('changePwd.html')
    pwd = request.form['pwd']
    s = mysql.Sql()
    r = s.sqlstr('''
        UPDATE TEACHER SET t_password = %s where t_id='%s'
    ''' % (pwd, session['user']['t_id']))
    return '提交完成'

#获取当前session的用户名
@app.route('/getusername', methods=['POST'])
@wrapper
def getusername():
    return session['user']['t_id']

#跳转评分用户页面
@app.route('/index', methods=['GET'])
@wrapper
def index():
    # return render_template('index.html')
    return redirect('/teacherScore')

#评分页面
@app.route('/teacherScore', methods=['GET'])
@wrapper
def teacherScore():
    return render_template('teacherScore.html')


#获取员工信息
@app.route('/getTeacherinfo', methods=['POST'])
@wrapper
def getTeacherinfo():
    #匿名用户不验证
    s = mysql.Sql()
    if ("anonymous" not in session['user']['t_id']):
        r = s.search("SELECT count FROM TEACHER WHERE t_id='%s'" %
                    session['user']['t_id'])
        #判断是否已经评分
        if(r[0]['count'] == 0):
            return jsonify([{'t_name': "已评分或无权限"}])
    r = s.search('''
        SELECT t_name,t_id,order1,zu_id FROM TEACHER WHERE kind!=0 and kind!=5
    ''')#排除管理员和匿名账号

    # for i in r:
    #     if(i['zu_id']==session['user']['zu_id'] and session['user']['kind']==4):
    #         i['order1']-=200
            
    return jsonify(r)




#添加员工接口
@app.route('/addTeacher', methods=['GET', 'POST'])
@wrapper
def addTeacher():
    # id 姓名 密码 部门id 组id 类型（1普通2副处3正处4校级5匿名） 次数
    if request.method == 'GET':
        return render_template('addTeacher.html')
    try:
        f = request.files['file']
        f.save(secure_filename(f.filename))

        d = excel.get_teachers(f.filename)

        s = mysql.Sql()
        # 保存admin pwd
        r = s.search("SELECT * FROM TEACHER WHERE kind=0 or kind=5")

        # 清空表
        s.sqlstr("truncate table t_geifen")
        s.sqlstr("truncate table t_defen")
        s.sqlstr("truncate table bu_geifen")
        s.sqlstr("truncate table bu_defen")
        s.sqlstr("SET FOREIGN_KEY_CHECKS=0")
        s.sqlstr("truncate table teacher")
        s.sqlstr("SET FOREIGN_KEY_CHECKS=1")

        # 存入admin
        for i in r:
            s.sqlstr(
                """
                INSERT INTO TEACHER(t_id, t_name, t_password, bumen_id, zu_id, kind, count, count_bu) 
                VALUES("%s", "%s", "%s", %s, %s, %s, %s, %s)
                """ % (
                    i['t_id'], i['t_name'], i['t_password'], i['bumen_id'], i['zu_id'], i['kind'], i['count'], i['count_bu']
                ))

        for i in d:
            sql_str = '''
                INSERT INTO TEACHER(
                    t_id,t_name,t_password, bumen_id, zu_id, kind,count,count_bu,order1
                    )
                VALUES ("%s","%s", "%s", %s, %s ,%s,%s,%s,%s)
            ''' % (
                i,
                d[i][0],
                d[i][1],
                d[i][2],
                d[i][3],
                d[i][4],
                d[i][5],
                d[i][6],
                d[i][7]
            )
            sql_str = sql_str.replace("None", "NULL")
            s.sqlstr(sql_str)
    except:
        print(traceback.format_exc())
        return traceback.format_exc()
    return "提交完成"

#管理端获取所有教师
@app.route('/getTeacherAllinfo', methods=['GET', 'POST'])
@wrapper
def getTeacherAllinfo():
    if request.method == 'GET':
        return render_template('getTeacherAllinfo.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM TEACHER
        '''
    )
    return jsonify(r)

#获取给分表
@app.route('/getTeacherGeifen', methods=['GET', 'POST'])
@wrapper
def getTeacherGeifen():
    if request.method == 'GET':
        return render_template('getTeacherGeifen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM t_geifen
        '''
    )
    return jsonify(r)

#获取得分表
@app.route('/getTeacherDefen', methods=['GET', 'POST'])
@wrapper
def getTeacherDefen():
    if request.method == 'GET':
        return render_template('getTeacherDefen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT t_name,score FROM teacher,t_defen WHERE t_defen.t_id = teacher.t_id
        '''
    )
    return jsonify(r)

#提交打分
@app.route('/postTeacherScore', methods=['POST'])
@wrapper
def postTeacherScore():
    #{"0011": ["---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---"],}

    j = request.form['json']
    d = json.loads(j)

    s = mysql.Sql()

    #校验
    temp_dict=dict()
    for i in d:
        temp_dict[i]=0
        for num,u in enumerate(d[i]):
            if u=="---请选择---":
                return "提交出错！请检查是否有空项"
            temp_dict[i]+=int(u)  #给每个人的总分

    #10%的低于 80，10%高于 90
    n=0 #低于80的计数
    n1=0 #高于90的计数
    for i in temp_dict:
        if temp_dict[i]<800:
            n+=1
        if temp_dict[i]>900:
            n1+=1
    if(n>len(temp_dict)*0.1 and n1<=len(temp_dict)*0.1):
        pass
    else:
        return "提交出错！不符合 至少10%的低于80，最多10%高于90"
    for i in d:#############################################################################################
        sql_str = '''
            INSERT INTO t_geifen(
                t_idfrom,t_idto, t_num1,t_num2,t_num3,t_num4,t_num5, t_num6,t_num7,t_num8,t_num9,t_num10
                )
            VALUES ("%s", "%s", %s, %s,%s,%s,%s, %s, %s,%s,%s,%s)
        ''' % (
            session['user']['t_id'],
            i,
            int(d[i][0]),
            int(d[i][1]),
            int(d[i][2]),
            int(d[i][3]),
            int(d[i][4]),
            int(d[i][5]),
            int(d[i][6]),
            int(d[i][7]),
            int(d[i][8]),
            int(d[i][9]),
        )
        s.sqlstr(sql_str)

    # 更改已打分标志
    s.sqlstr("UPDATE TEACHER SET count = 0 WHERE t_id='%s'" %
             session['user']['t_id'])

    return "提交完成"

#检查未打分的用户
@app.route('/checkTeacherCount', methods=['POST'])
@wrapper
def checkTeacherCount():
    s = mysql.Sql()
    counts = s.search("SELECT t_id,count FROM TEACHER")
    l = list()
    for i in counts:
        if(i['count'] == 1):
            l.append(i['t_id'])
    return jsonify(l)

#将结果收集到得分表
@app.route('/collectTeacherScore', methods=['POST'])
@wrapper
def collectTeacherScore():
    s = mysql.Sql()
    t_ids = s.search('''
        SELECT t_id FROM TEACHER
    ''')
    d = dict()
    for i in t_ids:
        t_id = i['t_id']
        r = s.search('''
            SELECT * FROM t_geifen WHERE t_idto='%s'
        ''' % (t_id)
        )  # r is list
        d[t_id] = r

    # 清空得分表
    s.sqlstr("truncate table t_defen")
    for i in d:
        #遍历每个人
        if len(d[i]) == 0:
            continue
        scorelist=list()
        for u in d[i]:
            #遍历每个人对他的评分
            score1=0
            for num,y in enumerate(u):
                if num >=2:
                    score1+=u[y]
            scorelist.append(score1)
        
        score = statistics.mean(scorelist)
        s.sqlstr('''
        INSERT INTO t_defen(
            t_id,score
            )
         VALUES ("%s", %s)
        ''' % (
            i,
            score
        ))
    return "提交完成"

# --------------------------------------------BUMEN-----------------------------------------------------------------------------------

#部门内评分获取员工信息
@app.route('/getDepartmentinfo', methods=['POST'])
@wrapper
def getDepartmentinfo():
    s = mysql.Sql()
    r = s.search("SELECT bumen_id,count_bu FROM TEACHER WHERE t_id='%s'" %
                 session['user']['t_id'])
    #判断是否已经评分
    if(r[0]['count_bu'] == 0):
        return jsonify([{'t_name': "已评分或无权限"}])
    r = s.search('''
        SELECT t_name,t_id,order1,zu_id FROM TEACHER WHERE kind!=0 and kind!=5 and bumen_id=%s
    '''%r[0]['bumen_id'])#排除管理员和匿名账号 只部门内员工
            
    return jsonify(r)

#部门内评分页面
@app.route('/departmentScore', methods=['GET'])
@wrapper
def departmentScore():
    return render_template('departmentScore.html')

#部门内给分表
@app.route('/getDepartmentGeifen', methods=['GET', 'POST'])
@wrapper
def getDepartmentGeifen():
    if request.method == 'GET':
        return render_template('getDepartmentGeifen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM bu_geifen
        '''
    )
    return jsonify(r)

#部门内得分表
@app.route('/getDepartmentDefen', methods=['GET', 'POST'])
@wrapper
def getDepartmentDefen():
    if request.method == 'GET':
        return render_template('getDepartmentDefen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT t_name,score FROM teacher,bu_defen WHERE bu_defen.t_id = teacher.t_id
        '''
    )
    return jsonify(r)


@app.route('/postDepartmentScore', methods=['POST'])
@wrapper
def postDepartmentScore():
    #{"0011": ["---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---","---请选择---"],}

    j = request.form['json']
    d = json.loads(j)

    s = mysql.Sql()

    #校验
    temp_dict=dict()
    for i in d:
        for num,u in enumerate(d[i]):
            if u=="---请选择---":
                return "提交出错！请检查是否有空项"
            if num not in temp_dict:
                temp_dict[num]=list()
            temp_dict[num].append(int(u))
    #10%的低于 80，10%高于 90
    for i in temp_dict:
        n=0 #低于80的计数
        n1=0 #高于90的计数
        for u in temp_dict[i]:
            if u<80:
                n+=1
            if u>90:
                n1+=1
        if(n>len(temp_dict[i])*0.1 and n1<=len(temp_dict[i])*0.1):
            pass
        else:
            return "提交出错！不符合10%的低于80，只能10%高于90"
            
            
    for i in d:#############################################################################################
        sql_str = '''
            INSERT INTO bu_geifen(
                t_idfrom,t_idto, t_num1,t_num2,t_num3,t_num4,t_num5, t_num6,t_num7,t_num8,t_num9,t_num10
                )
            VALUES ("%s", "%s", %s, %s,%s,%s,%s, %s, %s,%s,%s,%s)
        ''' % (
            session['user']['t_id'],
            i,
            int(d[i][0]),
            int(d[i][1]),
            int(d[i][2]),
            int(d[i][3]),
            int(d[i][4]),
            int(d[i][5]),
            int(d[i][6]),
            int(d[i][7]),
            int(d[i][8]),
            int(d[i][9]),
        )
        s.sqlstr(sql_str)

    # 更改已打分标志
    s.sqlstr("UPDATE TEACHER SET count_bu = 0 WHERE t_id='%s'" %
             session['user']['t_id'])

    return "提交完成"


@app.route('/checkBumenCount', methods=['POST'])
@wrapper
def checkBumenCount():
    s = mysql.Sql()
    counts = s.search("SELECT t_id,count_bu FROM TEACHER")
    l = list()
    for i in counts:
        if(i['count_bu'] == 1):
            l.append(i['t_id'])
    return jsonify(l)

#收集部门内得分表
@app.route('/collectDepartmentScore', methods=['POST'])
@wrapper
def collectDepartmentScore():
    s = mysql.Sql()
    t_ids = s.search('''
        SELECT t_id FROM TEACHER
    ''')
    d = dict()
    for i in t_ids:
        t_id = i['t_id']
        r = s.search('''
            SELECT * FROM bu_geifen WHERE t_idto='%s'
        ''' % (t_id)
        )  # r is list
        d[t_id] = r

    # 清空得分表
    s.sqlstr("truncate table bu_defen")
    for i in d:
        #遍历每个人
        if len(d[i]) == 0:
            continue
        scorelist=list()
        for u in d[i]:
            #遍历每个人对他的评分
            score1=0
            for num,y in enumerate(u):
                if num >=2:
                    score1+=u[y]
            scorelist.append(score1)
        
        score = statistics.mean(scorelist)
        s.sqlstr('''
        INSERT INTO bu_defen(
            t_id,score
            )
         VALUES ("%s", %s)
        ''' % (
            i,
            score
        ))
    return "提交完成"

#-------------------------------------管理端————————————————————————————————————————————————————
@app.route('/outputTeacher', methods=['GET'])
@wrapper
def outputTeacher():
    s = mysql.Sql()
    r = s.search("SELECT * FROM TEACHER")
    src = excel.output_excel(r, 'teacher')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputTeacherDefen', methods=['GET'])
@wrapper
def outputTeacherDefen():
    s = mysql.Sql()
    r = s.search(
        "SELECT t_name,score FROM teacher,t_defen WHERE t_defen.t_id=teacher.t_id")
    src = excel.output_excel(r, 'TeacherDefen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputTeacherGeifen', methods=['GET'])
@wrapper
def outputTeacherGeifen():
    s = mysql.Sql()
    r = s.search("SELECT * FROM t_geifen")
    src = excel.output_excel(r, 'TeacherGeifen')
    return send_from_directory('output', src, as_attachment=True)

@app.route('/outputDepartmentDefen', methods=['GET'])
@wrapper
def outputDepartmentDefen():
    s = mysql.Sql()
    r = s.search(
        "SELECT t_name,score FROM teacher,bu_defen WHERE bu_defen.t_id=teacher.t_id")
    src = excel.output_excel(r, 'DepartmentDefen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputDepartmentGeifen', methods=['GET'])
@wrapper
def outputDepartmentGeifen():
    s = mysql.Sql()
    r = s.search("SELECT * FROM bu_geifen")
    src = excel.output_excel(r, 'DepartmentGeifen')
    return send_from_directory('output', src, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
