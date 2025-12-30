#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动评分脚本
通过调用API自动完成所有人的教师和部门评分
"""

import requests
import csv
import random
import time
import json

# API基础URL
BASE_URL = "http://127.0.0.1:5000"

# 评分等级映射 (用于教师评分)
GRADES = ['A', 'B', 'C', 'D']
# A的权重更高，模拟真实评分倾向
GRADE_WEIGHTS = [0.5, 0.3, 0.15, 0.05]


class AutoScorer:
    def __init__(self):
        self.session = requests.Session()
        self.current_user = None

    def login(self, username, password):
        """登录系统"""
        url = f"{BASE_URL}/login"
        data = {
            't_id': username,
            'password': password
        }
        try:
            response = self.session.post(url, data=data, timeout=10)
            if response.status_code == 200:
                self.current_user = username
                print(f"✓ 用户 {username} 登录成功")
                return True
            else:
                print(f"✗ 用户 {username} 登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 用户 {username} 登录异常: {e}")
            return False

    def logout(self):
        """登出系统"""
        url = f"{BASE_URL}/logout"
        try:
            self.session.get(url, timeout=10)
            print(f"✓ 用户 {self.current_user} 已登出")
            self.current_user = None
        except:
            pass

    def get_teachers_to_score(self):
        """获取当前用户可以评价的教师列表"""
        url = f"{BASE_URL}/getTeacherinfo"
        try:
            response = self.session.post(url, timeout=10)
            if response.status_code == 200:
                teachers = response.json()
                # 过滤掉"已评分或无权限"的提示
                if teachers and isinstance(teachers, list):
                    if len(teachers) == 1 and teachers[0].get('t_name') in ["已评分或无权限", "无权限"]:
                        return []
                    return teachers
                return []
            else:
                print(f"  ✗ 获取教师列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"  ✗ 获取教师列表异常: {e}")
            return []

    def get_departments_to_score(self):
        """获取当前用户可以评价的部门列表"""
        url = f"{BASE_URL}/getBumeninfo"
        try:
            response = self.session.post(url, timeout=10)
            if response.status_code == 200:
                departments = response.json()
                # 过滤掉"已评分或无权限"的提示
                if departments and isinstance(departments, list):
                    if len(departments) == 1 and departments[0].get('bumen_name') in ["已评分或无权限", "无权限"]:
                        return []
                    return departments
                return []
            else:
                print(f"  ✗ 获取部门列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"  ✗ 获取部门列表异常: {e}")
            return []

    def submit_teacher_scores(self, scores_json):
        """提交教师评分

        Args:
            scores_json: str, JSON字符串，格式为 {"11":"A", "12":"B", ...}
                   其中第一位是维度(1-5)，其余是教师ID
        """
        if not scores_json:
            return True

        url = f"{BASE_URL}/postTeacherScore"
        try:
            # 使用form data格式提交
            data = {'json': scores_json}
            response = self.session.post(url, data=data, timeout=10)

            if response.status_code == 200:
                result = response.text
                if "提交完成" in result:
                    print(f"  ✓ 提交教师评分成功")
                    return True
                else:
                    print(f"  ✗ 提交教师评分失败: {result}")
                    return False
            else:
                print(f"  ✗ 提交教师评分失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 提交教师评分异常: {e}")
            return False

    def submit_department_scores(self, scores_json):
        """提交部门评分

        Args:
            scores_json: str, JSON字符串，格式为 {"11":"95.5", "12":"90", ...}
                   其中第一位是维度(1-4)，其余是部门ID
        """
        if not scores_json:
            return True

        url = f"{BASE_URL}/postBumenScore"
        try:
            # 使用form data格式提交
            data = {'json': scores_json}
            response = self.session.post(url, data=data, timeout=10)

            if response.status_code == 200:
                result = response.text
                if "提交完成" in result:
                    print(f"  ✓ 提交部门评分成功")
                    return True
                else:
                    print(f"  ✗ 提交部门评分失败: {result}")
                    return False
            else:
                print(f"  ✗ 提交部门评分失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ 提交部门评分异常: {e}")
            return False

    def generate_teacher_score(self, teacher_id):
        """为一位教师生成5个维度的评分

        Returns:
            dict: {"1{teacher_id}": "A", "2{teacher_id}": "B", ...}
        """
        scores = {}
        for dimension in range(1, 6):  # 5个维度
            grade = random.choices(GRADES, weights=GRADE_WEIGHTS)[0]
            key = f"{dimension}{teacher_id}"
            scores[key] = grade
        return scores

    def generate_department_score(self, department_id):
        """为一个部门生成4个维度的评分

        Returns:
            dict: {"1{department_id}": "95.5", "2{department_id}": "92", ...}
        """
        scores = {}
        for dimension in range(1, 5):  # 4个维度
            # 生成1-25之间的随机分数，保留1位小数
            score = round(random.uniform(1, 25), 1)
            key = f"{dimension}{department_id}"
            scores[key] = str(score)
        return scores

    def score_for_user(self, user_id, password, user_name=""):
        """为单个用户完成评分流程"""
        print(f"\n{'='*60}")
        print(f"开始处理用户: {user_id} ({user_name})")
        print(f"{'='*60}")

        # 登录
        if not self.login(user_id, password):
            return False

        time.sleep(0.5)  # 短暂延迟，避免请求过快

        # 获取可评价的教师
        teachers = self.get_teachers_to_score()
        print(f"  可评价教师数量: {len(teachers)}")

        # 生成并提交教师评分
        if teachers:
            all_teacher_scores = {}
            for teacher in teachers:
                teacher_id = teacher['t_id']
                teacher_name = teacher.get('t_name', '')
                print(f"    - 为教师 {teacher_id}({teacher_name}) 生成评分")
                scores = self.generate_teacher_score(teacher_id)
                all_teacher_scores.update(scores)

            # 转换为JSON字符串并提交
            scores_json = json.dumps(all_teacher_scores)
            self.submit_teacher_scores(scores_json)

        time.sleep(0.5)

        # 获取可评价的部门
        departments = self.get_departments_to_score()
        print(f"  可评价部门数量: {len(departments)}")

        # 生成并提交部门评分
        if departments:
            all_department_scores = {}
            for dept in departments:
                dept_id = dept['bumen_id']
                dept_name = dept.get('bumen_name', '')
                print(f"    - 为部门 {dept_id}({dept_name}) 生成评分")
                scores = self.generate_department_score(dept_id)
                all_department_scores.update(scores)

            # 转换为JSON字符串并提交
            scores_json = json.dumps(all_department_scores)
            self.submit_department_scores(scores_json)

        # 登出
        self.logout()
        time.sleep(0.5)

        return True

    def collect_scores(self):
        """汇总计算最终得分"""
        print(f"\n{'='*60}")
        print("开始汇总计算最终得分")
        print(f"{'='*60}")

        # 以admin身份登录
        if not self.login('admin', 'admin'):
            print("✗ 无法以admin身份登录，汇总失败")
            return False

        time.sleep(0.5)

        # 先汇总部门得分
        print("正在汇总部门得分...")
        url = f"{BASE_URL}/collectBumenScore"
        try:
            response = self.session.post(url, timeout=30)
            if response.status_code == 200:
                result = response.text
                print(f"✓ 部门得分汇总完成: {result}")
            else:
                print(f"✗ 部门得分汇总失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 部门得分汇总异常: {e}")
            return False

        time.sleep(1)

        # 再汇总教师得分
        print("正在汇总教师得分...")
        url = f"{BASE_URL}/collectTeacherScore"
        try:
            response = self.session.post(url, timeout=30)
            if response.status_code == 200:
                result = response.text
                print(f"✓ 教师得分汇总完成: {result}")
            else:
                print(f"✗ 教师得分汇总失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 教师得分汇总异常: {e}")
            return False

        self.logout()
        return True

    def run(self, teacher_csv_path):
        """运行完整的自动评分流程

        Args:
            teacher_csv_path: 教师CSV文件路径
        """
        print("="*60)
        print("自动评分脚本启动")
        print("="*60)

        # 读取教师列表
        users = []
        try:
            with open(teacher_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    users.append({
                        't_id': row['t_id'],
                        't_password': row['t_password'],
                        't_name': row.get('t_name', ''),
                        'kind': row.get('kind', '')
                    })
            print(f"✓ 成功读取 {len(users)} 个用户")
        except Exception as e:
            print(f"✗ 读取教师CSV文件失败: {e}")
            return

        # 为每个用户执行评分
        success_count = 0
        fail_count = 0

        for user in users:
            user_id = user['t_id']
            password = user['t_password']
            user_name = user['t_name']

            # 跳过admin账号
            if user_id == 'admin':
                print(f"\n跳过admin账号")
                continue

            if self.score_for_user(user_id, password, user_name):
                success_count += 1
            else:
                fail_count += 1

            time.sleep(1)  # 用户之间延迟，避免请求过快

        # 汇总得分
        print(f"\n{'='*60}")
        print(f"所有用户评分完成")
        print(f"成功: {success_count}, 失败: {fail_count}")
        print(f"{'='*60}")

        # time.sleep(2)

        # 执行汇总计算
        # if self.collect_scores():
        #     print(f"\n{'='*60}")
        #     print("✓ 自动评分脚本执行完成！")
        #     print(f"{'='*60}")
        # else:
        #     print(f"\n{'='*60}")
        #     print("✗ 得分汇总失败，请检查日志")
        #     print(f"{'='*60}")


if __name__ == '__main__':
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = 'Teacher_test.csv'

    print(f"使用教师数据文件: {csv_file}")

    scorer = AutoScorer()
    scorer.run(csv_file)
