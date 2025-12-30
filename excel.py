import csv

def get_teachers(s):
    """读取教师数据（CSV格式）"""
    d = dict()
    with open(s, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for row in reader:
            if len(row) >= 9:
                Data1 = row[0]  # t_id
                Data2 = row[1]  # t_name
                Data3 = row[2]  # t_password
                Data4 = int(row[3]) if row[3] else None  # bumen_id
                Data5 = int(row[4]) if row[4] else None  # zu_id
                Data6 = int(row[5]) if row[5] else None  # kind
                Data7 = int(row[6]) if row[6] else None  # count
                Data8 = int(row[7]) if row[7] else None  # count_bu
                Data9 = int(row[8]) if row[8] else None  # order1
                d[Data1] = [Data2, Data3, Data4, Data5, Data6, Data7, Data8, Data9]
    return d

def get_bumen(s):
    """读取部门数据（CSV格式）"""
    d = dict()
    with open(s, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for row in reader:
            if len(row) >= 6:
                Data1 = int(row[0])  # bumen_id
                Data2 = row[1]  # t_id
                Data3 = row[2]  # bumen_name
                Data4 = int(row[3]) if row[3] else None  # order1
                Data5 = int(row[4]) if row[4] else None  # bumen_type (1=教学单位, 2=党政群团机构, 3=教辅单位)
                Data6 = float(row[5]) if row[5] else None  # mubiao_jixiao_score (目标绩效考核得分)
                d[Data1] = [Data2, Data3, Data4, Data5, Data6]
    return d

def get_fenguan_guanxi(s):
    """读取分管关系（CSV格式）
    格式：第1列fuchu_t_id（副处级工号），第2列xiaoji_t_id（分管校领导工号）
    一个副处级可以有多行，对应多个分管校领导
    """
    relations = []
    with open(s, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for row in reader:
            if len(row) >= 2:
                fuchu_id = row[0]  # 副处级工号
                xiaoji_id = row[1]  # 校领导工号
                if fuchu_id and xiaoji_id:
                    relations.append((fuchu_id, xiaoji_id))
    return relations

def output_excel(d, name):
    """输出数据到CSV文件"""
    filepath = "output/" + name + ".csv"

    if len(d) == 0:
        return name + ".csv"

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # 写入表头（从第一条数据的键名获取）
        headers = list(d[0].keys())
        writer.writerow(headers)

        # 写入数据行
        for row in d:
            writer.writerow([row[key] for key in headers])

    return name + ".csv"


if __name__ == "__main__":
    # 测试读取
    d = get_teachers('Teacher_test.csv')
    print(d)
    d = get_bumen('Bumen_test.csv')
    print(d)
    d = get_fenguan_guanxi('FenguanGuanxi_test.csv')
    print(d)
