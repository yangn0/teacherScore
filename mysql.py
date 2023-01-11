import pymysql

# 创建教师表
Teacher = """
create table Teacher(
    t_id varchar(100) not null PRIMARY KEY,
    t_name varchar(100) not null,
    t_password varchar(100) not null,
    bumen_id int not null,
    zu_id int,
    kind int not null,
    count int not null,
    count_bu int not null,
    order1 int
    )
"""
#加入管理员用户 匿名用户
Teacher_admin = """INSERT INTO Teacher(t_id,t_name,t_password, bumen_id, zu_id, kind,count,count_bu) VALUES ("%s","%s", "%s", %s, %s ,%s,%s,%s)
""" % (
    'admin', 'admin', '123456', 0, 0, 0, 0, 0
)
Teacher_no = """INSERT INTO Teacher(t_id,t_name,t_password, bumen_id, zu_id, kind,count,count_bu) VALUES ("%s","%s", "%s", %s, %s ,%s,%s,%s)
""" % (
    'anonymous', 'anonymous', '123456', 0, 0, 5, 0, 0
)


# t_给分表
t_geifen = '''
create table t_geifen(
    t_idfrom varchar(100) not null,
    t_idto varchar(100) not null,
    t_num1 int not null,
    t_num2 int not null,
    t_num3 int not null,
    t_num4 int not null,
    t_num5 int not null,
    t_num6 int not null,
    t_num7 int not null,
    t_num8 int not null,
    t_num9 int not null,
    t_num10 int not null
)
'''

# t_得分表
t_defen = '''
create table t_defen(
    t_id varchar(100) not null PRIMARY KEY,
    score float not null,
    foreign key(t_id) references Teacher(t_id) on delete cascade on update cascade
);

'''

# bu_给分表
bu_geifen = '''
create table bu_geifen(
    t_idfrom varchar(100) not null,
    t_idto varchar(100) not null,
    t_num1 int not null,
    t_num2 int not null,
    t_num3 int not null,
    t_num4 int not null,
    t_num5 int not null,
    t_num6 int not null,
    t_num7 int not null,
    t_num8 int not null,
    t_num9 int not null,
    t_num10 int not null
    )
'''

# bu_得分表
bu_defen = '''
create table bu_defen(
    t_id varchar(100) not null PRIMARY KEY,
    score float not null,
    foreign key(t_id) references Teacher(t_id) on delete cascade on update cascade
    )
'''


class Sql:
    def __init__(self):
        self.db = pymysql.connect(host='localhost',  # 指定连接本地服务器
                                  user='root',    # 登录服务器 用的用户名
                                  password='yangning',  # 登录服务器用的密码
                                  database='YANGNING',    # 指定目标数据库
                                  charset='utf8')
        # 规定返回的值为字典类型，否则默认返回元组类型
        self.cursor = self.db.cursor(cursor=pymysql.cursors.DictCursor)

    def __del__(self):
        # 关闭数据库连接
        self.db.close()

    def sqlstr(self, sql_str):
        try:
            # 执行sql语句
            self.cursor.execute(sql_str)
            # 提交到数据库执行
            self.db.commit()
        except Exception as err:
            # 如果发生错误则回滚
            self.db.rollback()
            raise err

    def search(self, sql_str):
        try:
            # 执行SQL语句
            self.cursor.execute(sql_str)
            # 获取所有记录列表
            results = self.cursor.fetchall()
            return results
        except Exception as err:
            self.db.rollback()
            raise err

    def init_table(self):
        try:
            # 执行sql语句
            self.cursor.execute(Teacher)
            self.cursor.execute(t_geifen)
            self.cursor.execute(t_defen)
            self.cursor.execute(bu_geifen)
            self.cursor.execute(bu_defen)

            # 提交到数据库执行
            self.db.commit()
        except Exception as err:
            # 如果发生错误则回滚
            self.db.rollback()
            raise err


if __name__ == "__main__":
    '''
    # 建库
    '''
    try:
        conn=pymysql.connect(
            host='localhost',
            user='root',
            passwd='yangning',
        )
        cur=conn.cursor()
        create_database_sql='CREATE DATABASE IF NOT EXISTS yangning DEFAULT CHARSET utf8 COLLATE utf8_general_ci;'
        cur.execute(create_database_sql)
        cur.close()
        print('创建数据库 yangning 成功！')
    except pymysql.Error as e:
        print('pymysql.Error: ',e.args[0],e.args[1])

    '''
    建表
    '''
    s = Sql()
    try:
        # 执行sql语句
        s.cursor.execute(Teacher)
        s.cursor.execute(Teacher_admin)
        s.cursor.execute(Teacher_no)
        s.cursor.execute(t_geifen)
        s.cursor.execute(t_defen)
        s.cursor.execute(bu_geifen)
        s.cursor.execute(bu_defen)

        # 提交到数据库执行
        s.db.commit()
        print("建表成功！")
    except Exception as err:
        # 如果发生错误则回滚
        s.db.rollback()
        raise err
