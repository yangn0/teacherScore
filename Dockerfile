FROM python:3.12
WORKDIR /teacherScore

COPY requirement.txt ./
RUN pip install --no-cache-dir -r requirement.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD [ "sh", "-c", "python mysql.py && gunicorn start:app -c ./gunicorn.conf.py"]