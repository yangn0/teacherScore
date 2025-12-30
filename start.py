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
        SELECT * FROM teacher WHERE t_id='%s' and t_password='%s'
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
        UPDATE teacher SET t_password = %s where t_id='%s'
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
    r = s.search("SELECT count FROM teacher WHERE t_id='%s'" %
                 session['user']['t_id'])
    if(r[0]['count'] == 0):
        return jsonify([{'t_name': "已评分或无权限"}])

    # 根据评分人类型返回不同的待评分干部列表
    user_kind = session['user']['kind']
    user_bumen = session['user']['bumen_id']
    user_id = session['user']['t_id']

    if user_kind == 1:
        # 普通人员：只能评本单位的处级干部（作为"本单位教职工"）
        r = s.search('''
            SELECT t_name,t_id,order1,zu_id FROM teacher
            WHERE (kind=2 OR kind=3) AND bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 2:
        # 副处级：只能评本单位的处级干部（作为"本单位班子成员"）
        r = s.search('''
            SELECT t_name,t_id,order1,zu_id FROM teacher
            WHERE (kind=2 OR kind=3) AND bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 3:
        # 正处级：根据所属部门类型决定评分范围
        # 先查询评分人所属部门的类型
        user_bumen_info = s.search('''
            SELECT bumen_type FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)

        if len(user_bumen_info) == 0:
            return jsonify([{'t_name': "无权限"}])

        user_bumen_type = user_bumen_info[0]['bumen_type']

        if user_bumen_type == 2:
            # 党政群团机构正处级：可以评全校所有处级干部
            r = s.search('''
                SELECT t_name,t_id,order1,zu_id FROM teacher WHERE (kind=2 OR kind=3)
            ''')
        elif user_bumen_type == 1:
            # 教学单位正处级：可以评本单位 + 党政群团(type=2) + 教辅单位(type=3)的处级干部
            r = s.search('''
                SELECT t_name,t_id,order1,zu_id FROM teacher
                WHERE (kind=2 OR kind=3)
                AND (bumen_id=%s OR bumen_id IN (
                    SELECT bumen_id FROM bumen WHERE bumen_type IN (2, 3)
                ))
            ''' % user_bumen)
        elif user_bumen_type == 3:
            # 教辅单位正处级：可以评本单位 + 党政群团(type=2) + 教辅单位(type=3)的处级干部
            r = s.search('''
                SELECT t_name,t_id,order1,zu_id FROM teacher
                WHERE (kind=2 OR kind=3)
                AND (bumen_id=%s OR bumen_id IN (
                    SELECT bumen_id FROM bumen WHERE bumen_type IN (2, 3)
                ))
            ''' % user_bumen)
        else:
            return jsonify([{'t_name': "无权限"}])

    elif user_kind == 4:
        # 校级领导：可以评所有正处级 + 自己分管的副处级
        # 查询自己分管的副处级ID列表
        fenguan_fuchu = s.search('''
            SELECT fuchu_t_id FROM fenguan_guanxi WHERE xiaoji_t_id='%s'
        ''' % user_id)
        fenguan_fuchu_ids = [row['fuchu_t_id'] for row in fenguan_fuchu]

        if len(fenguan_fuchu_ids) > 0:
            # 有分管的副处级，查询所有正处级 + 分管的副处级
            fuchu_ids_str = "','".join(fenguan_fuchu_ids)
            r = s.search('''
                SELECT t_name,t_id,order1,zu_id FROM teacher
                WHERE kind=3 OR (kind=2 AND t_id IN ('%s'))
            ''' % fuchu_ids_str)
        else:
            # 没有分管的副处级，只查询所有正处级
            r = s.search('''
                SELECT t_name,t_id,order1,zu_id FROM teacher WHERE kind=3
            ''')
    else:
        # 其他情况无权限
        return jsonify([{'t_name': "无权限"}])

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
        r = s.search("SELECT * FROM teacher WHERE kind=0")

        # 清空表
        s.sqlstr("truncate table t_geifen")
        s.sqlstr("truncate table t_defen")
        s.sqlstr("truncate table bu_geifen")
        s.sqlstr("truncate table bu_defen")
        s.sqlstr("truncate table fenguan_guanxi")
        s.sqlstr("SET FOREIGN_KEY_CHECKS=0")
        s.sqlstr("truncate table teacher")
        s.sqlstr("SET FOREIGN_KEY_CHECKS=1")

        # 存入admin
        for i in r:
            s.sqlstr(
                """
                INSERT INTO teacher(t_id, t_name, t_password, bumen_id, zu_id, kind, count, count_bu)
                VALUES("%s", "%s", "%s", %s, %s, %s, %s, %s)
                """ % (
                    i['t_id'], i['t_name'], i['t_password'], i['bumen_id'], i['zu_id'], i['kind'], i['count'], i['count_bu']
                ))

        for i in d:
            sql_str = '''
                INSERT INTO teacher(
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


@app.route('/addFenguanGuanxi', methods=['GET', 'POST'])
@wrapper
def addFenguanGuanxi():
    """导入分管关系
    Excel格式：第1列副处级工号，第2列分管校领导工号
    """
    if request.method == 'GET':
        return render_template('addFenguanGuanxi.html')
    try:
        f = request.files['file']
        f.save(secure_filename(f.filename))

        relations = excel.get_fenguan_guanxi(f.filename)

        s = mysql.Sql()
        # 清空分管关系表
        s.sqlstr("truncate table fenguan_guanxi")

        # 插入分管关系
        for fuchu_id, xiaoji_id in relations:
            sql_str = '''
                INSERT INTO fenguan_guanxi(fuchu_t_id, xiaoji_t_id)
                VALUES ("%s", "%s")
            ''' % (fuchu_id, xiaoji_id)
            s.sqlstr(sql_str)

        return "提交完成"
    except:
        print(traceback.format_exc())
        return traceback.format_exc()


@app.route('/getFenguanGuanxi', methods=['GET', 'POST'])
@wrapper
def getFenguanGuanxi():
    """查看分管关系"""
    if request.method == 'GET':
        return render_template('getFenguanGuanxi.html')
    s = mysql.Sql()
    # 查询分管关系，并关联教师姓名
    r = s.search('''
        SELECT
            fg.fuchu_t_id,
            t1.t_name as fuchu_name,
            t1.bumen_id as fuchu_bumen_id,
            b1.bumen_name as fuchu_bumen_name,
            fg.xiaoji_t_id,
            t2.t_name as xiaoji_name
        FROM fenguan_guanxi fg
        LEFT JOIN teacher t1 ON fg.fuchu_t_id = t1.t_id
        LEFT JOIN teacher t2 ON fg.xiaoji_t_id = t2.t_id
        LEFT JOIN bumen b1 ON t1.bumen_id = b1.bumen_id
        ORDER BY fg.fuchu_t_id, fg.xiaoji_t_id
    ''')
    return jsonify(r)


@app.route('/getTeacherAllinfo', methods=['GET', 'POST'])
@wrapper
def getTeacherAllinfo():
    if request.method == 'GET':
        return render_template('getTeacherAllinfo.html')
    s = mysql.Sql()
    r = s.search(
        '''
        SELECT * FROM teacher
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

    # 查询当前用户实际能评价的教师数量（使用与getTeacherinfo相同的权限过滤逻辑）
    user_id = session['user']['t_id']
    user_bumen = session['user']['bumen_id']
    user_kind = session['user']['kind']

    if user_kind == 1:
        # 普通人员：只能评本部门的副处级和正处级
        r = s.search('''
            SELECT t_id FROM teacher WHERE (kind=2 OR kind=3) AND bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 2:
        # 副处级：可以评本部门的正处级和副处级（包括自己）
        r = s.search('''
            SELECT t_id FROM teacher WHERE (kind=2 OR kind=3) AND bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 3:
        # 正处级：根据部门类型确定评分范围
        user_bumen_info = s.search('''
            SELECT bumen_type FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)

        if len(user_bumen_info) == 0:
            return "提交出错！用户部门信息不存在"

        user_bumen_type = user_bumen_info[0]['bumen_type']

        if user_bumen_type == 2:
            # 党政群团机构正处级：可以评所有副处级和正处级
            r = s.search('''
                SELECT t_id FROM teacher WHERE (kind=2 OR kind=3)
            ''')
        elif user_bumen_type == 1:
            # 教学单位正处级：可以评本单位 + 党政群团(type=2) + 教辅(type=3)的副处和正处
            r = s.search('''
                SELECT t.t_id FROM teacher t
                LEFT JOIN bumen b ON t.bumen_id = b.bumen_id
                WHERE (t.kind=2 OR t.kind=3)
                AND (t.bumen_id=%s OR b.bumen_type IN (2, 3))
            ''' % user_bumen)
        elif user_bumen_type == 3:
            # 教辅单位正处级：可以评本单位 + 党政群团(type=2) + 教辅(type=3)的副处和正处
            r = s.search('''
                SELECT t.t_id FROM teacher t
                LEFT JOIN bumen b ON t.bumen_id = b.bumen_id
                WHERE (t.kind=2 OR t.kind=3)
                AND (t.bumen_id=%s OR b.bumen_type IN (2, 3))
            ''' % user_bumen)
        else:
            r = []
    elif user_kind == 4:
        # 校级领导：可以评所有正处级 + 自己分管的副处级
        fenguan_fuchu = s.search('''
            SELECT fuchu_t_id FROM fenguan_guanxi WHERE xiaoji_t_id='%s'
        ''' % user_id)
        fenguan_fuchu_ids = [row['fuchu_t_id'] for row in fenguan_fuchu]

        if len(fenguan_fuchu_ids) > 0:
            fuchu_ids_str = "','".join(fenguan_fuchu_ids)
            r = s.search('''
                SELECT t_id FROM teacher
                WHERE kind=3 OR (kind=2 AND t_id IN ('%s'))
            ''' % fuchu_ids_str)
        else:
            # 没有分管副处级，只评所有正处级
            r = s.search('''
                SELECT t_id FROM teacher WHERE kind=3
            ''')
    else:
        r = []

    count_t = len(r)
    if len(d2) != count_t:
        return f"提交出错！应评价{count_t}位教师，但只提交了{len(d2)}位"
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
    s.sqlstr("UPDATE teacher SET count = 0 WHERE t_id='%s'" %
             session['user']['t_id'])

    return "提交完成"


@app.route('/checkTeacherCount', methods=['POST'])
@wrapper
def checkTeacherCount():
    s = mysql.Sql()
    counts = s.search("SELECT t_id,count FROM teacher")
    l = list()
    for i in counts:
        if(i['count'] == 1):
            l.append(i['t_id'])
    return jsonify(l)


@app.route('/collectTeacherScore', methods=['POST'])
@wrapper
def collectTeacherScore():
    # 新规则：根据部门类型和职级采用不同权重计算
    # 处级干部得分 = 班子得分 × 比例 + 民主测评得分 × 比例
    # 重要：副处级使用"分管校领导"，正处级使用"全体校领导"

    s = mysql.Sql()
    # 获取所有处级和副处级干部
    teachers = s.search('''
        SELECT t_id, bumen_id, kind FROM teacher WHERE kind=2 OR kind=3
    ''')

    # 清空得分表
    s.sqlstr("truncate table t_defen")

    for teacher_info in teachers:
        t_id = teacher_info['t_id']
        teacher_bumen_id = teacher_info['bumen_id']
        teacher_kind = teacher_info['kind']  # 2=副处级, 3=正处级

        # 对于副处级，查询其分管校领导ID列表
        fenguan_xiaoji_ids = []
        if teacher_kind == 2:  # 副处级
            fenguan_result = s.search('''
                SELECT xiaoji_t_id FROM fenguan_guanxi WHERE fuchu_t_id='%s'
            ''' % (t_id))
            fenguan_xiaoji_ids = [row['xiaoji_t_id'] for row in fenguan_result]

        # 获取该干部所属部门的类型和班子得分
        bumen_info = s.search('''
            SELECT bumen_type FROM bumen WHERE bumen_id=%s
        ''' % (teacher_bumen_id))

        if len(bumen_info) == 0:
            continue

        bumen_type = bumen_info[0]['bumen_type']  # 1=教学单位, 2=党政群团, 3=教辅

        # 获取班子得分
        banzi_defen = s.search('''
            SELECT score FROM bu_defen WHERE bumen_id=%s
        ''' % (teacher_bumen_id))

        if len(banzi_defen) == 0:
            continue  # 如果没有班子得分，跳过

        banzi_score = banzi_defen[0]['score']

        # 获取该干部的所有民主测评评分记录
        geifen_records = s.search('''
            SELECT * FROM t_geifen WHERE t_idto='%s'
        ''' % (t_id))

        if len(geifen_records) == 0:
            continue

        # 分类存储各类评分人的民主测评分数
        xiaoji_scores = list()  # 校级领导民主测评（正处级用所有校领导，副处级用分管校领导）
        dangzheng_zhengchu_or_banzi_scores = list()  # 党政群团正处级或本单位班子成员（正处+副处）
        quanxiao_zhengchu_or_banzi_scores = list()  # 全校正处级或本单位班子成员（正处+副处）
        bendanwei_jiaozhi_scores = list()  # 本单位教职工民主测评

        for record in geifen_records:
            # 民主测评得分 = t_num1+t_num2+t_num3+t_num4+t_num5
            minzhu_score = record['t_num1'] + record['t_num2'] + record['t_num3'] + record['t_num4'] + record['t_num5']

            # 查询评分人信息
            pingfenren_info = s.search('''
                SELECT kind, bumen_id FROM teacher WHERE t_id='%s'
            ''' % (record['t_idfrom']))

            if len(pingfenren_info) == 0:
                continue

            pingfenren_kind = pingfenren_info[0]['kind']
            pingfenren_bumen = pingfenren_info[0]['bumen_id']

            # 校级领导(kind=4)
            if pingfenren_kind == 4:
                # 对于副处级，只统计分管校领导的评分
                if teacher_kind == 2:  # 副处级
                    if record['t_idfrom'] in fenguan_xiaoji_ids:
                        xiaoji_scores.append(minzhu_score)
                else:  # 正处级，使用所有校领导
                    xiaoji_scores.append(minzhu_score)

            # 正处级(kind=3)
            elif pingfenren_kind == 3:
                # 判断是否本单位班子成员（同部门的正处级）
                is_bendanwei_banzi = (pingfenren_bumen == teacher_bumen_id)

                # 判断是否党政群团正处级
                is_dangzheng = False
                pingfenren_bumen_info = s.search('''
                    SELECT bumen_type FROM bumen WHERE bumen_id=%s
                ''' % (pingfenren_bumen))

                if len(pingfenren_bumen_info) > 0 and pingfenren_bumen_info[0]['bumen_type'] == 2:
                    is_dangzheng = True

                # "党政群团正处级或本单位班子成员"
                if is_dangzheng or is_bendanwei_banzi:
                    dangzheng_zhengchu_or_banzi_scores.append(minzhu_score)

                # "全校正处级或本单位班子成员" - 所有正处级都满足
                quanxiao_zhengchu_or_banzi_scores.append(minzhu_score)

            # 副处级(kind=2) - 只有本单位的副处级才算班子成员
            elif pingfenren_kind == 2:
                if pingfenren_bumen == teacher_bumen_id:
                    # 本单位副处级是班子成员，需要归入两个班子成员列表
                    dangzheng_zhengchu_or_banzi_scores.append(minzhu_score)
                    quanxiao_zhengchu_or_banzi_scores.append(minzhu_score)

            # 普通人员/教职工(kind=1)
            elif pingfenren_kind == 1:
                # 判断是否本单位教职工
                if pingfenren_bumen == teacher_bumen_id:
                    bendanwei_jiaozhi_scores.append(minzhu_score)

        # 计算各类民主测评的平均值
        xiaoji_avg = sum(xiaoji_scores) / len(xiaoji_scores) if xiaoji_scores else 0
        dangzheng_or_banzi_avg = sum(dangzheng_zhengchu_or_banzi_scores) / len(dangzheng_zhengchu_or_banzi_scores) if dangzheng_zhengchu_or_banzi_scores else 0
        quanxiao_or_banzi_avg = sum(quanxiao_zhengchu_or_banzi_scores) / len(quanxiao_zhengchu_or_banzi_scores) if quanxiao_zhengchu_or_banzi_scores else 0
        bendanwei_jiaozhi_avg = sum(bendanwei_jiaozhi_scores) / len(bendanwei_jiaozhi_scores) if bendanwei_jiaozhi_scores else 0

        # 根据部门类型和职级选择计算公式
        if bumen_type == 1:  # 教学单位
            if teacher_kind == 3:  # 正处级
                # 班子得分×40% + (校领导×30% + 党政群团正处级与本单位班子成员×30% + 本单位教职工×40%)×60%
                part1_score = banzi_score * 0.4
                minzhu_ceping = xiaoji_avg * 0.3 + dangzheng_or_banzi_avg * 0.3 + bendanwei_jiaozhi_avg * 0.4
                part2_score = minzhu_ceping * 0.6
                part3_score = 0
                score = part1_score + part2_score
            else:  # 副处级 (kind=2)
                # 班子得分×30% + (分管校领导×20% + 党政群团正处级与本单位班子成员×30% + 本单位教职工×50%)×70%
                part1_score = banzi_score * 0.3
                minzhu_ceping = xiaoji_avg * 0.2 + dangzheng_or_banzi_avg * 0.3 + bendanwei_jiaozhi_avg * 0.5
                part2_score = minzhu_ceping * 0.7
                part3_score = 0
                score = part1_score + part2_score
        else:  # 党政群团机构(type=2)、教辅单位(type=3)
            if teacher_kind == 3:  # 正处级
                # 班子得分×40% + (校领导×40% + 全校正处级与本单位班子成员×30% + 本部门教职工×30%)×60%
                part1_score = banzi_score * 0.4
                minzhu_ceping = xiaoji_avg * 0.4 + quanxiao_or_banzi_avg * 0.3 + bendanwei_jiaozhi_avg * 0.3
                part2_score = minzhu_ceping * 0.6
                part3_score = 0
                score = part1_score + part2_score
            else:  # 副处级 (kind=2)
                # 班子得分×30% + (分管校领导×20% + 全校正处级与本单位班子成员×40% + 本部门教职工×40%)×70%
                part1_score = banzi_score * 0.3
                minzhu_ceping = xiaoji_avg * 0.2 + quanxiao_or_banzi_avg * 0.4 + bendanwei_jiaozhi_avg * 0.4
                part2_score = minzhu_ceping * 0.7
                part3_score = 0
                score = part1_score + part2_score

        # 插入得分记录
        s.sqlstr('''
        INSERT INTO t_defen(
            t_id,part1_score,part2_score,part3_score,score
            )
         VALUES ("%s", %s, %s, %s,%s)
        ''' % (
            t_id,
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
    r = s.search("SELECT count_bu FROM teacher WHERE t_id='%s'" %
                 session['user']['t_id'])
    if(r[0]['count_bu'] == 0):
        return jsonify([{'bumen_name': "已评分或无权限"}])

    # 根据评分人类型返回不同的待评分部门列表
    user_kind = session['user']['kind']
    user_bumen = session['user']['bumen_id']

    if user_kind == 1 or user_kind == 2:
        # 普通人员和副处级：只能评本部门（作为"本部门教职工"）
        r = s.search('''
            SELECT * FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 3:
        # 正处级：根据所属部门类型决定评分范围
        # 先查询评分人所属部门的类型
        user_bumen_info = s.search('''
            SELECT bumen_type FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)

        if len(user_bumen_info) == 0:
            return jsonify([{'bumen_name': "无权限"}])

        user_bumen_type = user_bumen_info[0]['bumen_type']

        if user_bumen_type == 2:
            # 党政群团机构正处级：可以评所有部门
            r = s.search('''
                SELECT * FROM bumen
            ''')
        elif user_bumen_type == 1:
            # 教学单位正处级：可以评自己部门 + 党政（type=2）和教辅（type=3）部门
            r = s.search('''
                SELECT * FROM bumen WHERE bumen_id=%s OR bumen_type IN (2, 3)
            ''' % user_bumen)
        elif user_bumen_type == 3:
            # 教辅单位正处级：可以评自己部门 + 党政（type=2）和教辅（type=3）部门
            r = s.search('''
                SELECT * FROM bumen WHERE bumen_id=%s OR bumen_type IN (2, 3)
            ''' % user_bumen)
        else:
            return jsonify([{'bumen_name': "无权限"}])

    elif user_kind == 4:
        # 校级领导：可以评所有部门
        r = s.search('''
            SELECT * FROM bumen
        ''')
    else:
        # 其他情况（如副处级）无部门评分权限
        return jsonify([{'bumen_name': "无权限"}])

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
        s.sqlstr("truncate table bu_mubiao_jixiao")

        for i in d:
            # 插入部门基本信息
            sql_str = '''
                INSERT INTO bumen(
                    bumen_id,t_id,bumen_name,order1,bumen_type)
                VALUES (%s,"%s","%s",%s,%s)
            ''' % (
                i,
                d[i][0],
                d[i][1],
                d[i][2],
                d[i][3]
            )
            sql_str = sql_str.replace("None", "NULL")
            s.sqlstr(sql_str)

            # 插入部门目标绩效
            sql_str2 = '''
                INSERT INTO bu_mubiao_jixiao(
                    bumen_id, mubiao_jixiao_score)
                VALUES (%s, %s)
            ''' % (i, d[i][4])
            sql_str2 = sql_str2.replace("None", "NULL")
            s.sqlstr(sql_str2)
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
        SELECT * FROM bumen
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

    # 查询当前用户实际能评价的部门数量（使用与getBumeninfo相同的权限过滤逻辑）
    user_bumen = session['user']['bumen_id']
    user_kind = session['user']['kind']

    if user_kind == 1 or user_kind == 2:
        # 普通人员和副处级：只能评本部门（作为"本部门教职工"）
        r = s.search('''
            SELECT bumen_id FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)
    elif user_kind == 3:
        # 正处级：根据部门类型确定评分范围
        user_bumen_info = s.search('''
            SELECT bumen_type FROM bumen WHERE bumen_id=%s
        ''' % user_bumen)

        if len(user_bumen_info) == 0:
            return "提交出错！用户部门信息不存在"

        user_bumen_type = user_bumen_info[0]['bumen_type']

        if user_bumen_type == 2:
            # 党政群团机构正处级：可以评所有部门
            r = s.search('SELECT bumen_id FROM bumen')
        elif user_bumen_type == 1:
            # 教学单位正处级：可以评自己部门 + 党政（type=2）和教辅（type=3）部门
            r = s.search('''
                SELECT bumen_id FROM bumen WHERE bumen_id=%s OR bumen_type IN (2, 3)
            ''' % user_bumen)
        elif user_bumen_type == 3:
            # 教辅单位正处级：可以评自己部门 + 党政（type=2）和教辅（type=3）部门
            r = s.search('''
                SELECT bumen_id FROM bumen WHERE bumen_id=%s OR bumen_type IN (2, 3)
            ''' % user_bumen)
        else:
            r = []
    elif user_kind == 4:
        # 校级领导：可以评所有部门
        r = s.search('SELECT bumen_id FROM bumen')
    else:
        r = []

    count_bumen = len(r)
    if len(d2) != count_bumen:
        return f"提交出错！应评价{count_bumen}个部门，但只提交了{len(d2)}个"
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
    s.sqlstr("UPDATE teacher SET count_bu = 0 WHERE t_id='%s'" %
             session['user']['t_id'])

    return "提交完成"


@app.route('/checkBumenCount', methods=['POST'])
@wrapper
def checkBumenCount():
    s = mysql.Sql()
    counts = s.search("SELECT t_id,count_bu FROM teacher")
    l = list()
    for i in counts:
        if(i['count_bu'] == 1):
            l.append(i['t_id'])
    return jsonify(l)


@app.route('/collectBumenScore', methods=['POST'])
@wrapper
def collectBumenScore():
    # 新规则（第十三条）：根据部门类型采用不同权重计算
    # 教学单位(type=1): 目标绩效×60% + (校领导×30% + 党政群团正处级×30% + 本单位教职工和正处副处×40%)×40%
    # 党政群团/教辅(type=2,3): 目标绩效×60% + (校领导×40% + 全校正处级×30% + 本部门教职工和副处×30%)×40%

    s = mysql.Sql()
    bumen_list = s.search('''
        SELECT bumen_id, bumen_type FROM bumen
    ''')

    # 清空得分表
    s.sqlstr("truncate table bu_defen")

    for bumen_info in bumen_list:
        bumen_id = bumen_info['bumen_id']
        bumen_type = bumen_info['bumen_type']

        # 获取该部门的目标绩效考核得分
        mubiao_result = s.search('''
            SELECT mubiao_jixiao_score FROM bu_mubiao_jixiao WHERE bumen_id=%s
        ''' % (bumen_id))

        if len(mubiao_result) == 0:
            continue  # 如果没有目标绩效数据，跳过

        mubiao_jixiao = mubiao_result[0]['mubiao_jixiao_score']

        # 获取该部门的所有民主测评评分记录
        geifen_records = s.search('''
            SELECT * FROM bu_geifen WHERE bumen_id=%s
        ''' % (bumen_id))

        if len(geifen_records) == 0:
            continue

        # 分类存储各类评分人的民主测评分数
        xiaoji_scores = list()  # 校级领导民主测评
        dangzheng_zhengchu_scores = list()  # 党政群团正处级民主测评
        quanxiao_zhengchu_scores = list()  # 全校正处级民主测评
        bendanwei_jiaozhi_fuzhengchu_scores = list()  # 本单位教职工和正处副处（教学单位）
        bendanwei_jiaozhi_fuchu_scores = list()  # 本部门教职工和副处（党政群团/教辅）

        for record in geifen_records:
            # 民主测评得分 = num1+num2+num3+num4
            minzhu_score = record['num1'] + record['num2'] + record['num3'] + record['num4']

            # 查询评分人信息
            pingfenren_info = s.search('''
                SELECT kind, bumen_id FROM teacher WHERE t_id='%s'
            ''' % (record['t_id']))

            if len(pingfenren_info) == 0:
                continue

            pingfenren_kind = pingfenren_info[0]['kind']
            pingfenren_bumen = pingfenren_info[0]['bumen_id']

            # 校级领导(kind=4)
            if pingfenren_kind == 4:
                xiaoji_scores.append(minzhu_score)

            # 正处级(kind=3)
            elif pingfenren_kind == 3:
                quanxiao_zhengchu_scores.append(minzhu_score)

                # 判断是否党政群团正处级（所属部门类型为2）
                pingfenren_bumen_info = s.search('''
                    SELECT bumen_type FROM bumen WHERE bumen_id=%s
                ''' % (pingfenren_bumen))

                if len(pingfenren_bumen_info) > 0 and pingfenren_bumen_info[0]['bumen_type'] == 2:
                    dangzheng_zhengchu_scores.append(minzhu_score)

                # 如果是本单位的正处级，加入到"本单位教职工和正处副处"
                if pingfenren_bumen == bumen_id:
                    bendanwei_jiaozhi_fuzhengchu_scores.append(minzhu_score)

            # 副处级(kind=2)
            elif pingfenren_kind == 2:
                # 如果是本单位/本部门的副处级
                if pingfenren_bumen == bumen_id:
                    bendanwei_jiaozhi_fuzhengchu_scores.append(minzhu_score)  # 教学单位用
                    bendanwei_jiaozhi_fuchu_scores.append(minzhu_score)  # 党政群团/教辅用

            # 普通人员/教职工(kind=1)
            elif pingfenren_kind == 1:
                # 判断是否本单位/本部门教职工
                if pingfenren_bumen == bumen_id:
                    bendanwei_jiaozhi_fuzhengchu_scores.append(minzhu_score)  # 教学单位用
                    bendanwei_jiaozhi_fuchu_scores.append(minzhu_score)  # 党政群团/教辅用

        # 计算各类民主测评的平均值
        xiaoji_avg = sum(xiaoji_scores) / len(xiaoji_scores) if xiaoji_scores else 0
        dangzheng_zhengchu_avg = sum(dangzheng_zhengchu_scores) / len(dangzheng_zhengchu_scores) if dangzheng_zhengchu_scores else 0
        quanxiao_zhengchu_avg = sum(quanxiao_zhengchu_scores) / len(quanxiao_zhengchu_scores) if quanxiao_zhengchu_scores else 0
        bendanwei_jiaozhi_fuzhengchu_avg = sum(bendanwei_jiaozhi_fuzhengchu_scores) / len(bendanwei_jiaozhi_fuzhengchu_scores) if bendanwei_jiaozhi_fuzhengchu_scores else 0
        bendanwei_jiaozhi_fuchu_avg = sum(bendanwei_jiaozhi_fuchu_scores) / len(bendanwei_jiaozhi_fuchu_scores) if bendanwei_jiaozhi_fuchu_scores else 0

        # 根据部门类型计算总分
        if bumen_type == 1:  # 教学单位
            # 目标绩效×60% + (校领导×30% + 党政群团正处级×30% + 本单位教职工和正处副处×40%)×40%
            part1_score = mubiao_jixiao * 0.6
            minzhu_ceping = xiaoji_avg * 0.3 + dangzheng_zhengchu_avg * 0.3 + bendanwei_jiaozhi_fuzhengchu_avg * 0.4
            part2_score = minzhu_ceping * 0.4
            score = part1_score + part2_score
        else:  # 党政群团机构(type=2)、教辅单位(type=3)
            # 目标绩效×60% + (校领导×40% + 全校正处级×30% + 本部门教职工和副处×30%)×40%
            part1_score = mubiao_jixiao * 0.6
            minzhu_ceping = xiaoji_avg * 0.4 + quanxiao_zhengchu_avg * 0.3 + bendanwei_jiaozhi_fuchu_avg * 0.3
            part2_score = minzhu_ceping * 0.4
            score = part1_score + part2_score

        # 插入得分记录
        s.sqlstr('''
        INSERT INTO bu_defen(
            bumen_id,part1_score,part2_score,score
            )
         VALUES (%s, %s, %s, %s)
        ''' % (
            bumen_id,
            part1_score,
            part2_score,
            score
        ))

    return "提交完成"


@app.route('/outputTeacher', methods=['GET'])
@wrapper
def outputTeacher():
    s = mysql.Sql()
    r = s.search("SELECT * FROM teacher")
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
    app.run("0.0.0.0",debug=True)
