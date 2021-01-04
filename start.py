from flask import Flask, request, jsonify
from flask import render_template
from flask import redirect, render_template, session, send_file, send_from_directory
from functools import wraps
import json
import mysql
import time
import os
import excel
from werkzeug.utils import secure_filename
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] =  "yangning" # os.urandom(24)设置一个随机24位字符串为加密盐
app.config.update(TEMPLATE_AUTO_RELOAD=True)

# 装饰器装饰多个视图函数


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


@app.route('/', methods=['GET'])
def test():
    return render_template('login.html')


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
    session["user"] = r[0]
    # 接入管理员端
    if(r[0]['kind'] == 0):
        return redirect("/addTeacher")
    return redirect("/index")


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


@app.route('/getusername', methods=['POST'])
@wrapper
def getusername():
    return session['user']['t_id']


@app.route('/index', methods=['GET'])
@wrapper
def index():
    # return render_template('index.html')
    return redirect('/teacherScore')


@app.route('/teacherScore', methods=['GET'])
@wrapper
def teacherScore():
    return render_template('teacherScore.html')


@app.route('/getTeacherinfo', methods=['POST'])
@wrapper
def getTeacherinfo():
    s = mysql.Sql()
    r = s.search("SELECT count FROM TEACHER WHERE t_id='%s'" %
                 session['user']['t_id'])
    if(r[0]['count'] == 0):
        return jsonify([{'t_name': "已评分或无权限"}])
    # -----------------------------------------------------------------------申静-------------------------------------------------------
    sj_ids = [1944, 1963]
    sjid = 1034
    if(session['user']['t_id'] in sj_ids):
        r = s.search('''
            SELECT t_name,t_id,order1,zu_id FROM TEACHER WHERE t_id='%s'
        ''' % sjid)

    elif(session['user']['kind'] == 1):
        r = s.search('''
            SELECT t_name,t_id,order1,zu_id FROM TEACHER WHERE (kind=2 or kind=3) and bumen_id=%s
        ''' % session['user']['bumen_id'])
    else:
        r = s.search('''
            SELECT t_name,t_id,order1,zu_id FROM TEACHER WHERE (kind=2 or kind=3)
        ''')
    for i in r:
        if(i['zu_id']==session['user']['zu_id'] and session['user']['kind']==4):
            i['order1']-=200
            
    return jsonify(r)


@app.route('/addTeacher', methods=['GET', 'POST'])
@wrapper
def addTeacher():
    # id 姓名 密码 部门id 组id 类型（1普通2副处3正处4校级） 次数
    if request.method == 'GET':
        return render_template('addTeacher.html')
    try:
        f = request.files['file']
        f.save(secure_filename(f.filename))

        d = excel.get_teachers(f.filename)

        s = mysql.Sql()
        # 保存admin pwd
        r = s.search("SELECT * FROM TEACHER WHERE kind=0")

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


@app.route('/getTeacherDefen', methods=['GET', 'POST'])
@wrapper
def getTeacherDefen():
    if request.method == 'GET':
        return render_template('getTeacherDefen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT t_name,part1_score,part2_score,part3_score,score FROM teacher,t_defen WHERE t_defen.t_id = teacher.t_id
        '''
    )
    return jsonify(r)


@app.route('/postTeacherScore', methods=['POST'])
@wrapper
def postTeacherScore():
    # t_idfrom t_idto num1 num2 num3 num4 num5
    j = request.form['json']
    d = json.loads(j)
    # {"11":"E","13":"E","14":"E","21":"B"}
    d_num = {'A': 9, 'B': 8, 'C': 7, 'D': 5}
    d2 = dict()
    for i in d:
        if(i[1:] not in d2):
            d2[i[1:]] = dict()
        d2[i[1:]][i[0]] = d_num[d[i]]

    s = mysql.Sql()

    # 查询总人数
    if(session['user']['kind'] == 1):
        count_t = s.search("SELECT COUNT(*) FROM TEACHER WHERE (kind=2 or kind=3) and bumen_id=%s"
                           % session['user']['bumen_id'])[0]['COUNT(*)']
    else:
        count_t = s.search(
            "SELECT COUNT(*) FROM TEACHER WHERE kind=2 or kind=3")[0]['COUNT(*)']

    if len(d2) != int(count_t):
        return "提交出错！请检查是否有空项"
    for i in d2:
        if(len(d2[i]) != 5):
            return "提交出错！请检查是否有空项"
    for i in d2:
        sql_str = '''
            INSERT INTO t_geifen(
                t_idfrom,t_idto, t_num1,t_num2,t_num3,t_num4,t_num5
                )
            VALUES ("%s", "%s", %s, %s,%s,%s,%s)
        ''' % (
            session['user']['t_id'],
            i,
            d2[i]['1'],
            d2[i]['2'],
            d2[i]['3'],
            d2[i]['4'],
            d2[i]['5']
        )
        s.sqlstr(sql_str)

    # 更改次数标志
    s.sqlstr("UPDATE TEACHER SET count = 0 WHERE t_id='%s'" %
             session['user']['t_id'])

    return "提交完成"


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


@app.route('/collectTeacherScore', methods=['POST'])
@wrapper
def collectTeacherScore():
    # t_id part1_score part2_score part3_score score
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
        if len(d[i]) == 0:
            continue
        putong = list()
        zhengchu = list()
        fuchu = list()
        xiaoji_zhixi = list()
        xiaoji = list()
        for u in d[i]:
            # 查询类型
            r = s.search('''
                SELECT kind FROM TEACHER WHERE t_id='%s'
            ''' % (u['t_idfrom'])
            )
            # 类型（1普通2副处3正处4校级） 30 40 30
            if(r[0]['kind'] == 1):
                zong = u['t_num1']+u['t_num2'] + \
                    u['t_num3']+u['t_num4']+u['t_num5']
                putong.append(zong)
            elif(r[0]['kind'] == 2):
                zong = u['t_num1']+u['t_num2'] + \
                    u['t_num3']+u['t_num4']+u['t_num5']
                fuchu.append(zong)
            elif(r[0]['kind'] == 3):
                zong = u['t_num1']+u['t_num2'] + \
                    u['t_num3']+u['t_num4']+u['t_num5']
                zhengchu.append(zong)
            elif(r[0]['kind'] == 4):
                zong = u['t_num1']+u['t_num2'] + \
                    u['t_num3']+u['t_num4']+u['t_num5']
                r_from = s.search('''
                    SELECT zu_id FROM TEACHER WHERE t_id='%s'
                ''' % (u['t_idfrom'])
                )
                r_to = s.search('''
                    SELECT zu_id FROM TEACHER WHERE t_id='%s'
                ''' % (u['t_idto'])
                )
                if(r_from[0]['zu_id'] == r_to[0]['zu_id']):
                    # 同组
                    xiaoji_zhixi.append(zong)
                else:
                    xiaoji.append(zong)

        
            putong_avg = 0
            zhengchu_avg = 0
            fuchu_avg = 0
            xiaoji_avg = 0
            xiaojizhixi_avg = 0
        try:
            putong_avg = sum(putong)/len(putong)
        except:
            pass
        try:
            zhengchu_avg = sum(zhengchu)/len(zhengchu)
        except:
            pass
        try:
            fuchu_avg = sum(fuchu)/len(fuchu)
        except:
            pass
        try:
            xiaoji_avg = sum(xiaoji)/len(xiaoji)
        except:
            pass
        try:
            xiaojizhixi_avg = sum(xiaoji_zhixi)/len(xiaoji_zhixi)
        except:
            pass

        # 权重
        part1_score = putong_avg * 0.3
        part2_score = (zhengchu_avg+fuchu_avg)/2*0.4
        part3_score = xiaoji_avg*0.2+xiaojizhixi_avg*0.1

        score = part1_score+part2_score+part3_score
        s.sqlstr('''
        INSERT INTO t_defen(
            t_id,part1_score,part2_score,part3_score,score
            )
         VALUES ("%s", %s, %s, %s,%s)
        ''' % (
            i,
            part1_score,
            part2_score,
            part3_score,
            score
        ))
    return "提交完成"

# --------------------------------------------BUMEN-----------------------------------------------------------------------------------
@app.route('/bumenScore', methods=['GET'])
@wrapper
def BumenScore():
    return render_template('bumenScore.html')


@app.route('/getBumeninfo', methods=['POST'])
@wrapper
def getBumeninfo():
    s = mysql.Sql()
    r = s.search("SELECT count_bu FROM TEACHER WHERE t_id='%s'" %
                 session['user']['t_id'])
    if(r[0]['count_bu'] == 0):
        return jsonify([{'bumen_name': "已评分或无权限"}])

    r = s.search('''
        SELECT * FROM bumen
    ''')
    return jsonify(r)


@app.route('/addBumen', methods=['GET', 'POST'])
@wrapper
def addBumen():
    if request.method == 'GET':
        return render_template('addBumen.html')
    try:
        f = request.files['file']
        f.save(secure_filename(f.filename))

        d = excel.get_bumen(f.filename)

        s = mysql.Sql()
        # 清空表
        s.sqlstr("truncate table bumen")
        s.sqlstr("truncate table bu_geifen")

        for i in d:
            sql_str = '''
                INSERT INTO BUMEN(
                    bumen_id,t_id,bumen_name,order1)
                VALUES (%s,"%s","%s",%s)
            ''' % (
                i,
                d[i][0],
                d[i][1],
                d[i][2]
            )
            sql_str = sql_str.replace("None", "NULL")
            s.sqlstr(sql_str)
    except:
        print(traceback.format_exc())
        return traceback.format_exc()
    return "提交完成"


@app.route('/getBumenAllinfo', methods=['GET', 'POST'])
@wrapper
def getBumenAllinfo():
    if request.method == 'GET':
        return render_template('getBumenAllinfo.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM BUMEN
        '''
    )
    return jsonify(r)


@app.route('/getBumenGeifen', methods=['GET', 'POST'])
@wrapper
def getBumenGeifen():
    if request.method == 'GET':
        return render_template('getBumenGeifen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM bu_geifen
        '''
    )
    return jsonify(r)


@app.route('/getBumenDefen', methods=['GET', 'POST'])
@wrapper
def getBumenDefen():
    if request.method == 'GET':
        return render_template('getBumenDefen.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT bumen_name,part1_score,part2_score,score FROM bumen,bu_defen WHERE bumen.bumen_id=bu_defen.bumen_id
        '''
    )
    return jsonify(r)


@app.route('/postBumenScore', methods=['POST'])
@wrapper
def postBumenScore():
    # bumen_id t_id num1 num2 num3 num4
    j = request.form['json']
    d = json.loads(j)
    # d_num = {'A': 9, 'B': 8, 'C': 7, 'D': 5, }
    d2 = dict()
    for i in d:
        if(i[1:] not in d2):
            d2[i[1:]] = dict()
        if(d[i] == ''):
            return "提交出错！请检查是否有空项"
        d2[i[1:]][i[0]] = float(d[i])

    s = mysql.Sql()
    # 查询正处级校级总人数
    # count_t = s.search("SELECT COUNT(*) FROM TEACHER WHERE kind=3 or kind=4 and bumen_id=%s"
    #                    % session['user']['bumen_id'])[0]['COUNT(*)']

    # 部门数
    count_bumen = s.search("SELECT COUNT(*) FROM bumen ")[0]['COUNT(*)']

    if len(d2) != int(count_bumen):
        return "提交出错！请检查是否有空项"
    for i in d2:
        if(len(d2[i]) != 4):
            return "提交出错！请检查是否有空项"

    for i in d2:
        sql_str = '''
            INSERT INTO bu_geifen(
                bumen_id,t_id,num1,num2,num3,num4
                )
            VALUES (%s, "%s", %s, %s,%s,%s)
        ''' % (
            i,
            session['user']['t_id'],
            d2[i]['1'],
            d2[i]['2'],
            d2[i]['3'],
            d2[i]['4'],
        )
        s.sqlstr(sql_str)
    # 更改次数标志
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


@app.route('/collectBumenScore', methods=['POST'])
@wrapper
def collectBumenScore():
    # bumen_id part1_score part2_score score
    s = mysql.Sql()
    bumen_ids = s.search('''
        SELECT bumen_id FROM bumen
    ''')
    d = dict()
    for i in bumen_ids:
        bumen_id = i['bumen_id']
        r = s.search('''
            SELECT * FROM bu_geifen WHERE bumen_id=%s
        ''' % (bumen_id)
        )  # r is list
        d[bumen_id] = r

    # 清空得分表
    s.sqlstr("truncate table bu_defen")

    for i in d:
        if len(d[i]) == 0:
            continue
        zhengchu = list()
        xiaoji = list()
        xiaoji_zhixi = list()
        for u in d[i]:
            # 查询类型
            r = s.search('''
                SELECT bumen_id,kind FROM TEACHER WHERE t_id='%s'
            ''' % (u['t_id'])
            )
            # 类型（1普通2副处3正处4校级）
            if(r[0]['kind'] == 3):
                zong = u['num1']+u['num2'] + \
                    u['num3']+u['num4']
                zhengchu.append(zong)
            elif(r[0]['kind'] == 4):
                zong = u['num1']+u['num2'] + \
                    u['num3']+u['num4']
                r_bumen = r[0]['bumen_id']
                bumen_id = i
                if(r_bumen == bumen_id):
                    # 同组
                    xiaoji_zhixi.append(zong)
                else:
                    xiaoji.append(zong)
        
            zhengchu_avg = 0
            xiaoji_avg = 0
            xiaojizhixi_avg = 0
        try:
            zhengchu_avg = sum(zhengchu)/len(zhengchu)
        except:
            pass
        try:
            xiaoji_avg = sum(xiaoji)/len(xiaoji)
        except:
            pass
        try:
            xiaojizhixi_avg = sum(xiaoji_zhixi)/len(xiaoji_zhixi)
        except:
            pass

        # 部门权重
        part1_score = zhengchu_avg*0.6
        # 直属0.1 非直属0.3
        # part2_score = xiaojizhixi_avg*0.1+xiaoji_avg*0.3
        part2_score = (xiaojizhixi_avg+xiaoji_avg)*0.4
        score = part1_score+part2_score
        s.sqlstr('''
        INSERT INTO bu_defen(
            bumen_id,part1_score,part2_score,score
            )
         VALUES (%s, %s, %s, %s)
        ''' % (
            i,
            part1_score,
            part2_score,
            score
        ))

    return "提交完成"


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
        "SELECT t_name,part1_score,part2_score,part3_score,score FROM teacher,t_defen WHERE t_defen.t_id=teacher.t_id")
    src = excel.output_excel(r, 'TeacherDefen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputTeacherGeifen', methods=['GET'])
@wrapper
def outputTeacherGeifen():
    s = mysql.Sql()
    r = s.search("SELECT * FROM t_geifen")
    src = excel.output_excel(r, 'TeacherGeifen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputBumen', methods=['GET'])
@wrapper
def outputBumen():
    s = mysql.Sql()
    r = s.search("SELECT * FROM bumen")
    src = excel.output_excel(r, 'Bumen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputBumenDefen', methods=['GET'])
@wrapper
def outputBumenDefen():
    s = mysql.Sql()
    r = s.search(
        "SELECT bumen_name,part1_score,part2_score,score FROM bumen,bu_defen WHERE bumen.bumen_id=bu_defen.bumen_id")
    src = excel.output_excel(r, 'BumenDefen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/outputBumenGeifen', methods=['GET'])
@wrapper
def outputBumenGeifen():
    s = mysql.Sql()
    r = s.search("SELECT * FROM bu_geifen")
    src = excel.output_excel(r, 'BumenGeifen')
    return send_from_directory('output', src, as_attachment=True)


@app.route('/clearTeacherGeifen', methods=['POST', 'GET'])
@wrapper
def clearTeacherGeifen():
    s = mysql.Sql()
    s.sqlstr("DELETE FROM t_geifen where t_idfrom='%s'" %
             session['user']['t_id'])
    s.sqlstr("UPDATE teacher SET count = 1 where t_id='%s'" %
             session['user']['t_id'])
    return "提交完成"


@app.route('/clearBumenGeifen', methods=['POST', "GET"])
@wrapper
def clearBumenGeifen():
    if(session['user']['kind'] != 3 and session['user']['kind'] != 4):
        return "无权限"
    s = mysql.Sql()
    s.sqlstr("DELETE FROM bu_geifen where t_id='%s'" %
             session['user']['t_id'])
    s.sqlstr("UPDATE teacher SET count_bu = 1 where t_id='%s'" %
             session['user']['t_id'])
    return "提交完成"


if __name__ == '__main__':
    app.run(debug=True)
